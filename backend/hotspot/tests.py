import hashlib
import hmac
import socket
import struct
from datetime import timedelta
from unittest.mock import patch
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from organizations.models import Organization, OrganizationMembership
from radius.models import NasDevice, DisconnectRequest, DisconnectAttempt
from radius.disconnect import packet, parse_response, InvalidResponse, process_request, queue_disconnect
from payments.models import MpesaConfiguration, PaymentAttempt
from auditlog.models import AuditLog
from .models import HotspotPlan, Voucher, HotspotSession, HotspotSale, HotspotPurchase
from .services import issue_batch, authorize, commit, account, revoke, enforce_limits, digest, snapshot
from .payments import finalize_purchase
from rest_framework.exceptions import ValidationError


@override_settings(LINTECH_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode(), RADIUS_NAS_NETWORK='10.64.0.0/16', RADIUS_INTERNAL_TOKEN='bridge-test-key-'*4, RADIUS_ISOLATED=True)
class HotspotTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='ISP A', slug='hotspot-a')
        self.other = Organization.objects.create(name='ISP B', slug='hotspot-b')
        self.user = get_user_model().objects.create_user(username='hotspot-owner')
        OrganizationMembership.objects.create(organization=self.org, user=self.user, role='owner')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.nas = NasDevice.objects.create(organization=self.org, name='NAS A', source_ip='10.64.0.2', shared_secret='test-shared-secret-'*3)
        self.nas_b = NasDevice.objects.create(organization=self.other, name='NAS B', source_ip='10.64.0.3', shared_secret='other-shared-secret-'*3)
        self.plan = HotspotPlan.objects.create(organization=self.org, name='One hour', price=50, duration_seconds=3600,
                                               upload_kbps=1000, download_kbps=5000, quota_bytes=2**32+500)
        self.voucher = issue_batch(self.plan, 1).vouchers.get()
        self.mac, self.sid = 'AA:BB:CC:DD:EE:01', 'hotspot-session-1'

    def activate(self):
        authorize(self.nas, self.voucher.code, self.mac, self.sid)
        commit(self.nas, self.voucher.code, self.mac, self.sid)
        self.voucher.refresh_from_db()

    def accounting(self, kind='Start', **extra):
        values = {'Acct-Session-Id': self.sid, 'Calling-Station-Id': self.mac, 'Acct-Status-Type': kind,
                  'Framed-IP-Address': '192.0.2.10', **extra}
        account(self.nas, self.voucher.code, values)

    def test_invalid_voucher_rejected(self):
        with self.assertRaises(ValidationError): authorize(self.nas, 'HSinvalid', self.mac, self.sid)

    def test_authorization_does_not_activate_until_successful_authentication(self):
        limits = authorize(self.nas, self.voucher.code, self.mac, self.sid)
        self.voucher.refresh_from_db()
        self.assertIsNone(self.voucher.activated_at)
        self.assertEqual(limits['reply:Session-Timeout'], 3600)
        self.assertEqual(limits['reply:Mikrotik-Rate-Limit'], '1000k/5000k')
        self.assertEqual(limits['reply:Mikrotik-Total-Limit'], 500)
        self.assertEqual(limits['reply:Mikrotik-Total-Limit-Gigawords'], 1)
        commit(self.nas, self.voucher.code, self.mac, self.sid)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.status, 'active')
        self.assertEqual(self.voucher.expires_at-self.voucher.activated_at, timedelta(hours=1))

    def test_first_login_and_reauthentication_do_not_extend_expiry(self):
        self.activate(); expiry = self.voucher.expires_at
        self.accounting('Stop')
        authorize(self.nas, self.voucher.code, self.mac, 'next-session')
        commit(self.nas, self.voucher.code, self.mac, 'next-session')
        self.voucher.refresh_from_db(); self.assertEqual(self.voucher.expires_at, expiry)

    def test_expired_and_redeem_deadline_rejected(self):
        self.voucher.redeem_before = timezone.now()-timedelta(seconds=1); self.voucher.save()
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, self.mac, self.sid)
        self.voucher.redeem_before = None; self.voucher.expires_at = timezone.now()-timedelta(seconds=1); self.voucher.save()
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, self.mac, self.sid)

    def test_tenant_b_cannot_redeem_view_export_or_revoke_tenant_a(self):
        with self.assertRaises(ValidationError): authorize(self.nas_b, self.voucher.code, self.mac, self.sid)
        membership = OrganizationMembership.objects.get(user=self.user); membership.organization=self.other; membership.save()
        for path in [f'/api/hotspot/vouchers/{self.voucher.pk}/', f'/api/hotspot/batches/{self.voucher.batch_id}/export/']:
            response = self.client.post(path) if 'export' in path else self.client.get(path)
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(f'/api/hotspot/vouchers/{self.voucher.pk}/revoke/').status_code, 404)

    def test_device_binding_and_pending_race(self):
        authorize(self.nas, self.voucher.code, self.mac, self.sid)
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, 'AA:BB:CC:DD:EE:02', 'other')
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, self.mac, 'other')
        commit(self.nas, self.voucher.code, self.mac, self.sid)
        self.accounting('Stop')
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, 'AA:BB:CC:DD:EE:02', 'other')

    def test_stale_accounting_does_not_allow_duplicate_active_session(self):
        self.activate(); self.accounting()
        HotspotSession.objects.update(updated_at=timezone.now()-timedelta(hours=1))
        Voucher.objects.filter(pk=self.voucher.pk).update(reservation_until=timezone.now()-timedelta(minutes=1))
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, self.mac, 'new')

    def test_revoke_queues_specific_disconnect_and_blocks_reauth(self):
        self.activate(); self.accounting()
        revoke(self.voucher)
        item = DisconnectRequest.objects.get()
        self.assertEqual(item.session_id, self.sid)
        self.assertEqual(item.reason, 'revoked')
        with self.assertRaises(ValidationError): authorize(self.nas, self.voucher.code, self.mac, 'new')

    def test_accounting_start_interim_stop_monotonic_and_quota(self):
        self.activate(); self.accounting()
        self.accounting('Interim-Update', **{'Acct-Input-Octets':100, 'Acct-Output-Octets':200})
        self.accounting('Interim-Update', **{'Acct-Input-Octets':1, 'Acct-Output-Octets':2})
        session = HotspotSession.objects.get()
        self.assertEqual((session.upload_bytes, session.download_bytes), (100,200))
        self.accounting('Interim-Update', **{'Acct-Input-Gigawords':1, 'Acct-Input-Octets':500})
        self.voucher.refresh_from_db(); self.assertEqual(self.voucher.status, 'exhausted')
        self.assertEqual(DisconnectRequest.objects.get().reason, 'quota')
        self.accounting('Stop', **{'Acct-Terminate-Cause':'Session-Timeout'})
        session.refresh_from_db(); self.assertIsNotNone(session.stopped_at)
        self.assertEqual(session.terminate_cause, 'Session-Timeout')

    def test_accounting_without_successful_authentication_rejected(self):
        with self.assertRaises(ValidationError): self.accounting()

    def test_expiry_worker_queues_disconnect_without_faking_stop(self):
        self.activate(); self.accounting()
        Voucher.objects.filter(pk=self.voucher.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
        enforce_limits()
        self.assertEqual(DisconnectRequest.objects.get().reason, 'expired')
        self.assertIsNone(HotspotSession.objects.get().stopped_at)

    def test_plan_edit_does_not_change_voucher_entitlement(self):
        self.plan.duration_seconds=20; self.plan.download_kbps=999; self.plan.save()
        self.voucher.refresh_from_db(); self.assertEqual(self.voucher.duration_seconds,3600)
        self.assertEqual(self.voucher.download_kbps,5000)

    def test_nas_secret_is_write_only_and_source_unique(self):
        response = self.client.get('/api/radius/nas/')
        self.assertNotIn('shared_secret', response.data['results'][0])
        body = {'name':'Duplicate','source_ip':self.nas.source_ip,'shared_secret':'A'*40}
        self.assertEqual(self.client.post('/api/radius/nas/',body).status_code,400)
        body['source_ip']='127.0.0.1'
        self.assertEqual(self.client.post('/api/radius/nas/',body).status_code,400)

    def test_viewer_cannot_generate_vouchers_or_change_nas(self):
        OrganizationMembership.objects.filter(user=self.user).update(role='viewer')
        self.assertEqual(self.client.post('/api/hotspot/batches/',{'plan_id':self.plan.pk,'count':2}).status_code,403)
        self.assertEqual(self.client.patch(f'/api/radius/nas/{self.nas.pk}/',{'is_active':False}).status_code,403)

    def test_batch_limit_and_export_is_explicit_audited_no_store(self):
        self.assertEqual(self.client.post('/api/hotspot/batches/',{'plan_id':self.plan.pk,'count':201}).status_code,400)
        listed = self.client.get('/api/hotspot/vouchers/').data['results'][0]
        self.assertNotIn('code', listed)
        response = self.client.post(f'/api/hotspot/batches/{self.voucher.batch_id}/export/')
        self.assertEqual(response['Cache-Control'],'no-store')
        self.assertEqual(response.data['vouchers'][0]['code'], self.voucher.code)
        self.assertTrue(AuditLog.objects.filter(action='hotspot.vouchers_exported').exists())
        self.assertNotIn(self.voucher.code, str(list(AuditLog.objects.values('metadata'))))

    def test_cash_sale_is_once_and_not_generated_batch_revenue(self):
        self.assertEqual(self.client.get('/api/hotspot/summary/').data['received'],0)
        url = f'/api/hotspot/vouchers/{self.voucher.pk}/sale/'
        self.assertEqual(self.client.post(url).status_code,201)
        self.assertEqual(self.client.post(url).status_code,400)
        self.assertEqual(self.client.get('/api/hotspot/summary/').data['received'],50)

    def test_bridge_requires_internal_key_and_matching_source_and_tenant(self):
        client=APIClient(); url='/api/internal/radius/authorize/10.64.0.2/'
        body={'User-Name':self.voucher.code,'NAS-IP-Address':'10.64.0.2','Calling-Station-Id':self.mac,'Acct-Session-Id':self.sid}
        self.assertEqual(client.post(url,body,format='json').status_code,403)
        auth={'HTTP_X_LINTECH_RADIUS_KEY':'bridge-test-key-'*4}
        self.assertEqual(client.post(url,body,format='json',**auth).status_code,200)
        body['NAS-IP-Address']='10.64.0.3'
        self.assertEqual(client.post(url,body,format='json',**auth).status_code,403)
        self.assertEqual(client.post('/api/internal/radius/authorize/10.64.0.3/',body,format='json',**auth).status_code,400)

    def test_disconnect_ack_preserves_accounting_truth_and_audits(self):
        self.activate(); self.accounting(); revoke(self.voucher)
        item = DisconnectRequest.objects.get()
        with patch('radius.disconnect.transmit',return_value=('ack',None)):
            process_request(item.pk)
        item.refresh_from_db(); self.assertEqual(item.status,'acknowledged')
        session=HotspotSession.objects.get(); self.assertIsNone(session.stopped_at); self.assertIsNotNone(session.disconnected_at)
        self.assertTrue(AuditLog.objects.filter(action='radius.disconnect_ack').exists())
        self.assertEqual(self.client.get('/api/radius/disconnects/').data['results'][0]['events'][0]['result'],'ack')
        self.assertNotIn(self.voucher.code, str(self.client.get('/api/radius/disconnects/').data))

    def test_disconnect_timeouts_retry_then_exhaust_and_nak_is_recorded(self):
        item=queue_disconnect(self.nas,'subscriber','s1')
        with patch('radius.disconnect.transmit',side_effect=socket.timeout):
            for _ in range(5):
                DisconnectRequest.objects.filter(pk=item.pk).update(next_attempt_at=timezone.now())
                process_request(item.pk)
        item.refresh_from_db(); self.assertEqual(item.status,'failed'); self.assertEqual(item.attempts,5)
        self.assertEqual(DisconnectAttempt.objects.count(),5)
        other=queue_disconnect(self.nas,'subscriber','s2')
        with patch('radius.disconnect.transmit',return_value=('nak',503)): process_request(other.pk)
        other.refresh_from_db(); self.assertEqual(other.status,'not_found')

    def test_payment_success_issues_once_and_failure_issues_nothing(self):
        config=MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',environment='sandbox')
        attempt=PaymentAttempt.objects.create(organization=self.org,payment_configuration=config,amount=50,service_type='hotspot',purpose='hotspot_purchase',
            phone_number='254712345678',account_reference='test',status='failed')
        purchase=HotspotPurchase.objects.create(nas=self.nas,plan=self.plan,price=50,attempt=attempt,token_hash=digest('test-token'),entitlement=snapshot(self.plan))
        with self.assertRaises(ValidationError): finalize_purchase(attempt.pk)
        self.assertEqual(HotspotSale.objects.count(),0)
        attempt.status='successful'; attempt.mpesa_receipt_number='HSRECEIPT001'; attempt.save()
        first=finalize_purchase(attempt.pk); second=finalize_purchase(attempt.pk)
        self.assertEqual(first.pk,second.pk); self.assertEqual(HotspotSale.objects.count(),1)
        purchase.refresh_from_db(); self.assertEqual(purchase.voucher_id,first.pk)
        attempt.refresh_from_db(); self.assertEqual(attempt.settlement_status,'settled')

    def test_purchase_token_required_and_not_disclosed_by_admin_list(self):
        self.assertEqual(APIClient().post('/api/hotspot/purchase-status/',{'purchase_token':'x'*50}).status_code,404)
        self.assertEqual(APIClient().get(f'/api/hotspot/public/{self.nas.public_id}/').status_code,200)

    @override_settings(PUBLIC_BASE_URL='https://billing.example.net')
    def test_stk_intent_is_durable_and_retry_does_not_send_second_prompt(self):
        import uuid
        from django.core.cache import cache
        from .payments import start_purchase
        cache.clear()
        MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',is_default=True)
        key=uuid.uuid4()
        result={'merchant_request_id':'merchant','checkout_request_id':'checkout','response_code':'0'}
        with patch('hotspot.payments.StkPushService.initiate',return_value=result) as send:
            first,token=start_purchase(self.nas,self.plan,'254712345678',key)
            second,again=start_purchase(self.nas,self.plan,'254712345678',key)
        self.assertEqual(send.call_count,1);self.assertEqual(first.pk,second.pk);self.assertEqual(token,again)
        self.assertEqual(first.attempt.status,'pending')
        with self.assertRaises(ValidationError):start_purchase(self.nas_b,self.plan,'254712345678',key)
        response=APIClient().post('/api/hotspot/purchase-status/',{'purchase_token':token})
        self.assertEqual(response.status_code,200);self.assertIsNone(response.data['voucher_code'])

    @override_settings(PUBLIC_BASE_URL='https://billing.example.net')
    def test_ambiguous_provider_timeout_preserves_intent_without_resubmitting(self):
        import uuid
        from django.core.cache import cache
        from .payments import start_purchase
        cache.clear()
        MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',is_default=True)
        key=uuid.uuid4()
        with patch('hotspot.payments.StkPushService.initiate',side_effect=TimeoutError) as send:
            first,token=start_purchase(self.nas,self.plan,'254711111111',key)
            second,again=start_purchase(self.nas,self.plan,'254711111111',key)
        self.assertEqual(send.call_count,1);self.assertEqual(first.initiation_status,'unconfirmed')
        self.assertTrue(PaymentAttempt.objects.filter(pk=first.attempt_id).exists())
        self.assertEqual(HotspotSale.objects.count(),0)

    def test_production_payment_requires_provider_query_confirmation(self):
        config=MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',environment='production')
        attempt=PaymentAttempt.objects.create(organization=self.org,payment_configuration=config,amount=50,service_type='hotspot',purpose='hotspot_purchase',
            phone_number='254712345678',account_reference='test',status='successful',mpesa_receipt_number='PRODRECEIPT')
        HotspotPurchase.objects.create(nas=self.nas,plan=self.plan,price=50,attempt=attempt,token_hash=digest('prod-token'),entitlement=snapshot(self.plan))
        with patch('hotspot.payments.StkPushService.query',return_value={'result_code':'1032'}):
            with self.assertRaises(ValidationError):finalize_purchase(attempt.pk)
        self.assertEqual(HotspotSale.objects.count(),0)
        with patch('hotspot.payments.StkPushService.query',return_value={'result_code':'0'}):finalize_purchase(attempt.pk)
        self.assertEqual(HotspotSale.objects.count(),1)

    def test_callback_success_queues_hotspot_fulfillment_without_pppoe_settlement(self):
        config=MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',environment='sandbox')
        attempt=PaymentAttempt.objects.create(organization=self.org,payment_configuration=config,amount=50,service_type='hotspot',purpose='hotspot_purchase',
            phone_number='254712345678',account_reference='test',checkout_request_id='hotspot-checkout',merchant_request_id='hotspot-merchant')
        purchase=HotspotPurchase.objects.create(nas=self.nas,plan=self.plan,price=50,attempt=attempt,token_hash=digest('callback-token'),entitlement=snapshot(self.plan))
        payload={'Body':{'stkCallback':{'CheckoutRequestID':'hotspot-checkout','MerchantRequestID':'hotspot-merchant','ResultCode':0,
            'CallbackMetadata':{'Item':[{'Name':'Amount','Value':50},{'Name':'MpesaReceiptNumber','Value':'CALLBACK001'},
            {'Name':'PhoneNumber','Value':254712345678},{'Name':'TransactionDate','Value':20261023120000}]}}}}
        client=APIClient()
        with patch('payments.views.async_task'):
            response=client.post(f'/hooks/stk/{config.callback_token}/result/',payload,format='json')
        self.assertEqual(response.status_code,200)
        from payments.tasks import process_successful_stk_payment
        result=process_successful_stk_payment(attempt.pk)
        self.assertTrue(result['settled']);purchase.refresh_from_db();self.assertIsNotNone(purchase.voucher_id)
        self.assertEqual(HotspotSale.objects.count(),1)
        process_successful_stk_payment(attempt.pk);self.assertEqual(HotspotSale.objects.count(),1)

    @override_settings(PUBLIC_BASE_URL='https://billing.example.net')
    def test_captive_template_has_only_our_nas_purchase_url_and_no_secret(self):
        response=self.client.get(f'/api/radius/nas/{self.nas.pk}/captive-template/')
        self.assertEqual(response.status_code,200)
        text=response.content.decode()
        self.assertIn(f'https://billing.example.net/hotspot/{self.nas.public_id}',text)
        self.assertNotIn(self.nas.shared_secret,text)

    def test_verified_disconnect_without_final_quota_accounting_blocks_new_allocation(self):
        self.activate();self.accounting();item=queue_disconnect(self.nas,self.voucher.code,self.sid)
        with patch('radius.disconnect.transmit',return_value=('ack',None)):process_request(item.pk)
        Voucher.objects.filter(pk=self.voucher.pk).update(reservation_until=timezone.now()-timedelta(minutes=1))
        with self.assertRaises(ValidationError):authorize(self.nas,self.voucher.code,self.mac,'next')
        self.accounting('Stop')
        authorize(self.nas,self.voucher.code,self.mac,'next')

    def test_operator_retry_retains_attempt_history_and_adds_bounded_budget(self):
        item=queue_disconnect(self.nas,'subscriber','retry-test')
        DisconnectRequest.objects.filter(pk=item.pk).update(status='failed',attempts=5)
        response=self.client.post(f'/api/radius/disconnects/{item.pk}/retry/')
        self.assertEqual(response.status_code,200)
        item.refresh_from_db();self.assertEqual(item.attempts,5);self.assertEqual(item.max_attempts,10)
        with patch('radius.disconnect.transmit',return_value=('ack',None)):process_request(item.pk)
        item.refresh_from_db();self.assertEqual(item.attempts,6);self.assertEqual(item.status,'acknowledged')
        self.assertTrue(AuditLog.objects.filter(action='radius.disconnect_retry_requested').exists())

    def test_registered_pppoe_status_failure_rolls_back_customer(self):
        from customers.models import CustomerProfile,AddressZone
        from mikrotik.models import MikrotikRouter,RouterInfo
        from customers.service import CustomerService
        zone=AddressZone.objects.create(organization=self.org,name='Status Zone')
        router=MikrotikRouter.objects.create(organization=self.org,name='NAS router',host=self.nas.source_ip,username='unused',password='unused')
        self.nas.router=router;self.nas.save()
        customer=CustomerProfile.objects.create(organization=self.org,zone=zone,customer_id='STATUS1',customer_name='Status customer',phone_number='0712345678',address='test')
        RouterInfo.objects.create(customer=customer,router=router,authentication_mode='radius',pppoe_name='generated',pppoe_pass='unchanged')
        with patch('radius.subscribers.RadiusProvisioningService.suspend_pppoe_customer'),patch('radius.subscribers.queue_customer',side_effect=RuntimeError('sensitive raw failure')):
            with self.assertRaises(ValidationError) as failure:CustomerService.update_customer_status(self.org,customer.customer_id,'disconnected')
        self.assertNotIn('sensitive raw failure',str(failure.exception))
        customer.refresh_from_db();self.assertEqual(customer.customer_status,'active')
        with patch('radius.subscribers.RadiusProvisioningService.suspend_pppoe_customer'),patch('radius.subscribers.queue_customer',return_value=True),patch('mikrotik.service.helpers.disconnect_pppoe_session_on_router') as router_api:
            updated,warning=CustomerService.update_customer_status(self.org,customer.customer_id,'disconnected')
        self.assertEqual(updated.customer_status,'disconnected');self.assertIsNone(warning);router_api.assert_not_called()

    def test_payment_admin_reads_never_expose_purchase_token_or_code(self):
        purchase=HotspotPurchase.objects.create(nas=self.nas,plan=self.plan,price=50,token_hash=digest('purchase-secret'),recovery_token='purchase-secret',entitlement=snapshot(self.plan))
        response=self.client.get('/api/hotspot/purchases/')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('purchase-secret',str(response.data));self.assertNotIn('recovery_token',str(response.data))
        response=self.client.post(f'/api/hotspot/vouchers/{self.voucher.pk}/reveal/')
        self.assertEqual(response.status_code,200);self.assertEqual(response['Cache-Control'],'no-store')
        self.assertEqual(response.data['code'],self.voucher.code)
        self.assertNotIn(self.voucher.code,str(list(AuditLog.objects.values('metadata'))))

    @override_settings(RADIUS_ISOLATED=False,PUBLIC_BASE_URL='https://billing.example.net')
    def test_legacy_mode_never_accepts_new_hotspot_payment_prompts(self):
        import uuid
        from .payments import start_purchase
        MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',is_default=True)
        with patch('hotspot.payments.StkPushService.initiate') as send:
            with self.assertRaises(ValidationError):start_purchase(self.nas,self.plan,'254712345678',uuid.uuid4())
        send.assert_not_called()
        self.assertFalse(APIClient().get(f'/api/hotspot/public/{self.nas.public_id}/').data['purchases_enabled'])

    def test_maintenance_schedule_install_is_idempotent(self):
        from django.core.management import call_command
        from django_q.models import Schedule
        import io
        for _ in range(2):call_command('install_hotspot_schedule',stdout=io.StringIO())
        schedules=Schedule.objects.filter(func='hotspot.tasks.network_access_maintenance')
        self.assertEqual(schedules.count(),1)
        self.assertEqual(schedules.get().minutes,1);self.assertEqual(schedules.get().repeats,-1)

    @override_settings(PUBLIC_BASE_URL='https://billing.example.net')
    def test_specific_hotspot_shortcode_takes_precedence_over_both_scope(self):
        import uuid
        from django.core.cache import cache
        from .payments import start_purchase
        cache.clear()
        MpesaConfiguration.objects.create(organization=self.org,service_scope='both',is_default=True)
        expected=MpesaConfiguration.objects.create(organization=self.org,service_scope='hotspot',is_default=True)
        result={'merchant_request_id':'m','checkout_request_id':'c','response_code':'0'}
        with patch('hotspot.payments.StkPushService.initiate',autospec=True,return_value=result) as send:
            purchase,_=start_purchase(self.nas,self.plan,'254712345678',uuid.uuid4())
        self.assertEqual(send.call_args.args[0].configuration.pk,expected.pk)
        self.assertEqual(purchase.attempt.payment_configuration_id,expected.pk)

    def test_access_logging_redacts_callback_token_and_authentication_headers(self):
        from core.access_logging import SafeAccessLogger
        from types import SimpleNamespace
        secret='private-webhook-token'
        env={'REQUEST_METHOD':'POST','RAW_URI':f'/hooks/stk/{secret}/result/?token=private-query',
             'PATH_INFO':f'/hooks/stk/{secret}/result/','SERVER_PROTOCOL':'HTTP/1.1',
             'HTTP_X_LINTECH_RADIUS_KEY':'private-radius-key','HTTP_AUTHORIZATION':'Bearer private-jwt',
             'HTTP_REFERER':'https://example.test/?token=private-referrer'}
        logger=SafeAccessLogger.__new__(SafeAccessLogger)
        result=logger.atoms(SimpleNamespace(status=200,sent=0,headers={'Set-Cookie':'private-cookie'}),
                            {'Authorization':'Bearer private-jwt','X-Lintech-Radius-Key':'private-radius-key'},env,timedelta(seconds=1))
        text=str(result)
        for value in [secret,'private-query','private-radius-key','private-jwt','private-cookie','private-referrer']:
            self.assertNotIn(value,text)
        self.assertIn('[redacted]',text)

    def test_nas_can_create_pppoe_router_without_administrator_credentials(self):
        from mikrotik.models import MikrotikRouter
        response=self.client.post('/api/radius/nas/',{'name':'AAA-only router','source_ip':'10.64.0.40',
            'shared_secret':'a-unique-test-nas-secret-'*2,'create_pppoe_router':True},format='json')
        self.assertEqual(response.status_code,201,response.data)
        router=MikrotikRouter.objects.get(pk=response.data['router'])
        self.assertEqual(router.organization_id,self.org.pk)
        self.assertEqual((router.username,router.password),('',''))
        self.assertNotIn('shared_secret',response.data)
        self.assertNotIn('create_pppoe_router',response.data)

    @override_settings(PUBLIC_BASE_URL='https://billing.example.net')
    def test_shared_hotspot_nat_does_not_limit_all_customers_to_five_purchases(self):
        import uuid
        from types import SimpleNamespace
        from django.core.cache import cache
        cache.clear()
        client=APIClient()
        with patch('hotspot.payments.start_purchase',return_value=(SimpleNamespace(pk=uuid.uuid4(),initiation_status='submitted'),'x'*50)):
            for n in range(6):
                response=client.post(f'/api/hotspot/public/{self.nas.public_id}/',{'plan_id':self.plan.pk,'phone_number':f'25471234567{n}','request_id':str(uuid.uuid4())})
                self.assertEqual(response.status_code,202,response.data)


class DisconnectProtocolTests(TestCase):
    def test_request_authenticator_and_message_authenticator(self):
        secret='independent-test-secret'
        request=packet('user','session','10.64.0.2',secret,identifier=9,timestamp=1000)
        self.assertEqual(request[4:20],hashlib.md5(request[:4]+bytes(16)+request[20:]+secret.encode()).digest())
        zeroed=request[:4]+bytes(16)+request[20:-16]+bytes(16)
        self.assertEqual(request[-16:],hmac.new(secret.encode(),zeroed,hashlib.md5).digest())
        header=struct.pack('!BBH',41,9,20)
        response=header+hashlib.md5(header+request[4:20]+secret.encode()).digest()
        self.assertEqual(parse_response(response,request,secret),('ack',None))
        for bad in [response[:-1], response[:4]+bytes(16), bytes([42])+response[1:]]:
            with self.assertRaises(InvalidResponse): parse_response(bad,request,secret)

    def test_response_message_authenticator_and_nak_error_cause(self):
        secret='independent-test-secret'
        request=packet('user','session','10.64.0.2',secret,identifier=8,timestamp=1000)
        attrs=bytes([101,6])+struct.pack('!I',503)+bytes([80,18])+bytes(16)
        header=struct.pack('!BBH',42,8,20+len(attrs))
        ma=hmac.new(secret.encode(),header+request[4:20]+attrs,hashlib.md5).digest()
        attrs=attrs[:-16]+ma
        response=header+hashlib.md5(header+request[4:20]+attrs+secret.encode()).digest()+attrs
        self.assertEqual(parse_response(response,request,secret),('nak',503))
        # Even a response with a valid outer digest must have a valid MA.
        attrs=attrs[:-16]+bytes(16)
        forged=header+hashlib.md5(header+request[4:20]+attrs+secret.encode()).digest()+attrs
        with self.assertRaises(InvalidResponse): parse_response(forged,request,secret)
