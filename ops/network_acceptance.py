#!/usr/bin/env python3
"""Real FreeRADIUS PAP/CHAP/accounting + simulated NAS Disconnect ACKs in an isolated network."""
import json, os, secrets, subprocess, sys, tempfile, time, uuid
from pathlib import Path
from cryptography.fernet import Fernet
ROOT=Path(__file__).resolve().parents[1]
BACKEND=os.environ.get('NETWORK_BACKEND_IMAGE','lintech-backend:hotspot-dev')
RADIUS=os.environ.get('NETWORK_RADIUS_IMAGE','lintech-freeradius:hotspot-dev')


def run(args,**kwargs):
    return subprocess.run(args,cwd=ROOT,check=True,**kwargs)


def main(backend_image=BACKEND, radius_image=RADIUS):
    suffix=uuid.uuid4().hex[:8]; network='lintech-wire-'+suffix
    subnet=f'172.29.{secrets.randbelow(200)+20}'
    names={key:f'lintech-test-{key}-{suffix}' for key in ['db','api','radius','nas-a','nas-b']}
    key=secrets.token_urlsafe(48); secret_a=secrets.token_hex(24);secret_b=secrets.token_hex(24)
    run(['docker','network','create','--internal','--subnet',subnet+'.0/24',network],stdout=subprocess.DEVNULL)
    try:
        with tempfile.NamedTemporaryFile(mode='w+',prefix='lintech-wire-') as env:
            env.write(f'DATABASE_URL=postgres://postgres@{names["db"]}/postgres\nDJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\nLINTECH_FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}\nDJANGO_ALLOWED_HOSTS=backend,localhost\nDJANGO_DEBUG=False\nLINTECH_RADIUS_INTERNAL_TOKEN={key}\nRADIUS_CLIENT_NETWORK={subnet}.0/24\nLINTECH_RADIUS_ISOLATED=1\nPOSTGRES_USER=postgres\nPOSTGRES_PASSWORD=temporary-isolated-test\nPOSTGRES_DB=postgres\nNAS_A={subnet}.10\nNAS_B={subnet}.11\nSECRET_A={secret_a}\nSECRET_B={secret_b}\n')
            env.flush()
            common=['--network',network,'--env-file',env.name]
            run(['docker','run','-d','--name',names['db'],'--network',network,'--network-alias','db','--tmpfs','/var/lib/postgresql/data','-e','POSTGRES_HOST_AUTH_METHOD=trust','postgres:16-alpine'],stdout=subprocess.DEVNULL)
            for _ in range(60):
                if subprocess.run(['docker','exec',names['db'],'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
                time.sleep(1)
            schema=run(['docker','run','--rm','--entrypoint','cat',radius_image,'/etc/freeradius/3.0/mods-config/sql/main/postgresql/schema.sql'],capture_output=True).stdout
            run(['docker','exec','-i',names['db'],'psql','-U','postgres','-v','ON_ERROR_STOP=1'],input=schema,stdout=subprocess.DEVNULL)
            run(['docker','run','--rm',*common,backend_image,'python','manage.py','migrate','--noinput'],stdout=subprocess.DEVNULL)
            seed='''import os,json,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()
from organizations.models import Organization
from radius.models import NasDevice
from hotspot.models import HotspotPlan
from hotspot.services import issue_batch
from customers.models import CustomerProfile,AddressZone
from mikrotik.models import MikrotikRouter,RouterInfo
from billing.models import Package
from radius.services import RadiusProvisioningService
org=Organization.objects.create(name='Wire ISP A',slug='wire-a');other=Organization.objects.create(name='Wire ISP B',slug='wire-b')
router=MikrotikRouter.objects.create(organization=org,name='Wire router',host=os.environ['NAS_A'],username='',password='')
nas=NasDevice.objects.create(organization=org,router=router,name='A',source_ip=os.environ['NAS_A'],shared_secret=os.environ['SECRET_A'])
NasDevice.objects.create(organization=other,name='B',source_ip=os.environ['NAS_B'],shared_secret=os.environ['SECRET_B'])
plan=HotspotPlan.objects.create(organization=org,name='Wire plan',price=50,duration_seconds=3600,upload_kbps=1000,download_kbps=5000,quota_bytes=10000)
codes={}
for label in ['A','Q','T','REVOKED','EXPIRED']:
 v=issue_batch(plan,1).vouchers.get()
 if label=='T':v.duration_seconds=1
 if label in ['REVOKED','EXPIRED']:v.status=label.lower()
 v.save();codes['CODE_'+label]=v.code
zone=AddressZone.objects.create(organization=org,name='Zone');package=Package.objects.create(organization=org,name='PPPoE',price=500,speed='5 Mbps')
c=CustomerProfile.objects.create(organization=org,zone=zone,package=package,customer_id='WIRE1',customer_name='Wire subscriber',phone_number='0712345678',address='test')
u=RadiusProvisioningService.build_radius_username(c);RouterInfo.objects.create(customer=c,router=router,authentication_mode='radius',pppoe_name=u,pppoe_pass='wire-pppoe-password')
RadiusProvisioningService.provision_pppoe_customer(c,password='wire-pppoe-password')
codes.update(CODE_PPP=u,PPP_PASSWORD='wire-pppoe-password');print(json.dumps(codes))
'''
            seeded=run(['docker','run','--rm','-i',*common,backend_image,'python','-'],input=seed.encode(),capture_output=True).stdout.decode().splitlines()[-1]
            codes=json.loads(seeded)
            for k,v in codes.items():env.write(f'{k}={v}\n')
            env.flush()
            run(['docker','run','-d','--name',names['api'],'--network-alias','backend',*common,backend_image],stdout=subprocess.DEVNULL)
            for _ in range(60):
                if subprocess.run(['docker','exec',names['api'],'curl','-fsS','http://localhost:8000/api/health/'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
                time.sleep(1)
            run(['docker','run','-d','--name',names['radius'],'--network-alias','radius',*common,radius_image,'freeradius','-f','-l','stdout'],stdout=subprocess.DEVNULL)
            for name,ip,secret,other in [('nas-a',subnet+'.10',secret_a,subnet+'.11'),('nas-b',subnet+'.11',secret_b,subnet+'.10')]:
                run(['docker','run','-d','--name',names[name],'--ip',ip,*common,'-e','OWN_SECRET='+secret,'-e','OWN_IP='+ip,'-e','OTHER_IP='+other,'-v',str(ROOT/'ops/radius_probe.py')+':/probe.py:ro',backend_image,'python','/probe.py','daemon'],stdout=subprocess.DEVNULL)
            time.sleep(3)
            def probe(kind,identity,nas='nas-a',sid='wire-session',extra=(),**counters):
                env_args=['-e','SESSION_ID='+sid]
                for k,v in counters.items():env_args+=['-e',f'{k}={v}']
                result=subprocess.run(['docker','exec',*env_args,names[nas],'python','/probe.py',kind,identity,*extra],capture_output=True)
                if result.returncode:
                    raise RuntimeError('Probe failed: '+result.stderr.decode()[-1200:])
                value=result.stdout.decode().splitlines()[-1]
                return json.loads(value)
            def code(source):
                return run(['docker','exec','-i',names['api'],'python','-'],input=("import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup()\n"+source).encode(),capture_output=True).stdout.decode().strip()
            def expect(value,expected,label):
                if value.get('code')!=expected:raise AssertionError(f'{label}: expected {expected}, received {value}')
                print('PASS:',label,flush=True)
            expect(probe('auth','A',extra=['--wrong-password']),3,'invalid voucher password rejected')
            assert code("from hotspot.models import Voucher;assert not Voucher.objects.filter(activated_at__isnull=False).exists()") == ''
            expect(probe('auth','HSinvalid'),3,'unknown voucher rejected')
            expect(probe('auth','REVOKED'),3,'revoked voucher rejected')
            expect(probe('auth','EXPIRED'),3,'expired voucher rejected')
            expect(probe('auth','A',nas='nas-b'),3,'tenant B cannot redeem tenant A voucher')
            expect(probe('auth','A',extra=['--wrong-secret']),'timeout','wrong NAS secret rejected')
            expect(probe('auth','A',extra=['--spoof-source']),3,'claimed NAS address cannot override packet source')
            response=probe('auth','A',extra=['--chap']);expect(response,2,'CHAP voucher authentication')
            assert response['rate']=='1000k/5000k' and response['session_timeout']<=3600 and response['quota']==10000
            print('PASS: speed, quota and Session-Timeout reply attributes',flush=True)
            expect(probe('auth','A',sid='second',extra=['--second-device']),3,'second device blocked')
            expect(probe('start','A'),5,'accounting Start acknowledged')
            expect(probe('interim','HSinvalid',sid='invalid-accounting'),'timeout','unknown voucher accounting is not acknowledged')
            expect(probe('interim','A',extra=['--spoof-source']),'timeout','spoofed NAS accounting is not acknowledged')
            expect(probe('interim','A',UPLOAD=123,DOWNLOAD=456,DURATION=30),5,'accounting interim acknowledged')
            assert code("from hotspot.models import HotspotSession;s=HotspotSession.objects.get(session_id='wire-session');assert (s.upload_bytes,s.download_bytes)==(123,456)") == ''
            code("from hotspot.models import Voucher;from hotspot.services import revoke;from radius.disconnect import process_request;from radius.models import DisconnectRequest;v=Voucher.objects.get(status='active');revoke(v);r=DisconnectRequest.objects.get(reason='revoked');process_request(r.pk);r.refresh_from_db();assert r.status=='acknowledged'")
            print('PASS: voucher revocation sends signed Disconnect-Request and validates NAS ACK',flush=True)
            expect(probe('stop','A',UPLOAD=123,DOWNLOAD=456,DURATION=31),5,'accounting Stop acknowledged')
            expect(probe('auth','A',sid='reconnect'),3,'revoked voucher cannot reconnect')
            expect(probe('auth','Q',sid='quota'),2,'quota voucher authentication')
            expect(probe('interim','Q',sid='quota',UPLOAD=10000),5,'quota accounting')
            code("from radius.models import DisconnectRequest;from radius.disconnect import process_request;r=DisconnectRequest.objects.get(reason='quota');process_request(r.pk);r.refresh_from_db();assert r.status=='acknowledged'")
            expect(probe('auth','Q',sid='after-quota'),3,'exhausted quota blocks reconnect')
            expect(probe('auth','T',sid='expiry'),2,'short-validity voucher authentication');time.sleep(2)
            code("from hotspot.services import enforce_limits;from radius.models import DisconnectRequest;from radius.disconnect import process_request;enforce_limits();r=DisconnectRequest.objects.get(reason='expired');process_request(r.pk);r.refresh_from_db();assert r.status=='acknowledged'")
            print('PASS: expiry worker disconnects with verified ACK',flush=True)
            expect(probe('auth','PPP',sid='pppoe'),2,'PPPoE authentication preserved on registered NAS')
            expect(probe('auth','PPP',nas='nas-b',sid='cross-pppoe'),3,'cross-tenant PPPoE rejected')
            expect(probe('start','PPP',sid='pppoe'),5,'PPPoE accounting on registered NAS')
            code("from customers.models import CustomerProfile;from customers.service import CustomerService;from radius.models import DisconnectRequest,RadiusCheck;from radius.disconnect import process_request;c=CustomerProfile.objects.get(customer_id='WIRE1');before=RadiusCheck.objects.get(attribute='Cleartext-Password').value;CustomerService.update_customer_status(c.organization,c.customer_id,'disconnected');r=DisconnectRequest.objects.get(reason='suspended');process_request(r.pk);r.refresh_from_db();assert r.status=='acknowledged';assert RadiusCheck.objects.get(attribute='Cleartext-Password').value==before")
            expect(probe('auth','PPP',sid='suspended-pppoe'),3,'suspended PPPoE blocks reconnect without RouterOS API')
            code("from customers.models import CustomerProfile;from customers.service import CustomerService;from radius.models import RadiusCheck;c=CustomerProfile.objects.get(customer_id='WIRE1');before=RadiusCheck.objects.get(attribute='Cleartext-Password').value;CustomerService.update_customer_status(c.organization,c.customer_id,'active');assert RadiusCheck.objects.get(attribute='Cleartext-Password').value==before")
            expect(probe('auth','PPP',sid='renewed-pppoe'),2,'PPPoE reactivation preserves supplied password')

            code("from radius.models import NasDevice,DisconnectRequest;from radius.disconnect import queue_disconnect,process_request;from django.utils import timezone;n=NasDevice.objects.get(name='A');r=queue_disconnect(n,'test','retry-once');process_request(r.pk);r.refresh_from_db();assert r.status=='retry';r.next_attempt_at=timezone.now();r.save();process_request(r.pk);r.refresh_from_db();assert r.status=='acknowledged' and r.attempts==2")
            print('PASS: lost Disconnect ACK retried and acknowledged',flush=True)
            code("from radius.models import NasDevice;from radius.disconnect import queue_disconnect,process_request;n=NasDevice.objects.get(name='A');r=queue_disconnect(n,'test','already-gone');process_request(r.pk);r.refresh_from_db();assert r.status=='not_found';r=queue_disconnect(n,'test','invalid-response');process_request(r.pk);r.refresh_from_db();assert r.status=='retry' and r.last_error=='invalid_response'")
            print('PASS: authenticated NAK and forged response handled safely',flush=True)
            print('PASS: isolated registered-NAS/Hotspot RADIUS protocol acceptance',flush=True)
    except Exception:
        # Save private test-only logs; do not print packet/credential dumps.
        directory=ROOT/'.local/network-failures';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        for key_name in ['radius','api','nas-a','nas-b']:
            output=subprocess.run(['docker','logs',names[key_name]],capture_output=True)
            path=directory/(suffix+'-'+key_name+'.log');path.write_bytes(output.stdout+output.stderr);path.chmod(0o600)
        raise
    finally:
        subprocess.run(['docker','rm','-f',*names.values()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        run(['docker','network','rm',network],stdout=subprocess.DEVNULL)

if __name__=='__main__': main()
