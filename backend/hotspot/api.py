from datetime import timedelta
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from core.pagination import CustomPagination
from organizations.mixins import OrganizationQuerySetMixin
from organizations.permissions import HasOrganizationRole, READ_ONLY_ROLES, BILLING_ROLES, NETWORK_ROLES, ADMIN_ROLES
from auditlog.services import AuditService
from radius.models import NasDevice
from .models import HotspotPlan, Voucher, VoucherBatch, HotspotSession, HotspotSale, HotspotPurchase
from . import services


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotspotPlan
        fields = ['id', 'name', 'price', 'duration_seconds', 'upload_kbps', 'download_kbps', 'quota_bytes', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        for field, maximum in [('duration_seconds', 31536000), ('upload_kbps', 10000000), ('download_kbps', 10000000)]:
            value = attrs.get(field, getattr(self.instance, field, 0))
            if not 1 <= value <= maximum:
                raise serializers.ValidationError({field: f'Use a value from 1 to {maximum}.'})
        quota = attrs.get('quota_bytes', getattr(self.instance, 'quota_bytes', None))
        if quota is not None and not 1 <= quota <= 2**53-1:
            raise serializers.ValidationError({'quota_bytes': 'Use a positive byte quota, or leave unlimited.'})
        price = attrs.get('price', getattr(self.instance, 'price', 0))
        if price < 1 or price != int(price):
            raise serializers.ValidationError({'price': 'Use a positive whole-KES price for STK compatibility.'})
        return attrs


class PlanViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = HotspotPlan.objects.all()
    serializer_class = PlanSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'retrieve': READ_ONLY_ROLES, 'create': ADMIN_ROLES,
                        'update': ADMIN_ROLES, 'partial_update': ADMIN_ROLES}

    def perform_create(self, serializer):
        obj = serializer.save(organization=self.get_organization())
        AuditService.log(request=self.request, organization=obj.organization, action='hotspot.plan_created', resource_type='HotspotPlan', resource_id=obj.pk)

    def perform_update(self, serializer):
        obj = serializer.save()
        AuditService.log(request=self.request, organization=obj.organization, action='hotspot.plan_updated', resource_type='HotspotPlan', resource_id=obj.pk)


class VoucherSerializer(serializers.ModelSerializer):
    used_bytes = serializers.SerializerMethodField()
    class Meta:
        model = Voucher
        fields = ['id', 'batch', 'plan_name', 'price', 'duration_seconds', 'upload_kbps', 'download_kbps', 'quota_bytes',
                  'status', 'activated_at', 'expires_at', 'redeem_before', 'bound_mac', 'used_bytes', 'created_at']
    def get_used_bytes(self, obj):
        return services.usage(obj)


class VoucherViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Voucher.objects.select_related('organization', 'batch')
    serializer_class = VoucherSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'retrieve': READ_ONLY_ROLES, 'revoke': NETWORK_ROLES, 'sale': BILLING_ROLES, 'reveal': BILLING_ROLES}

    def get_queryset(self):
        rows = super().get_queryset()
        if self.request.query_params.get('batch'):
            batch_id = serializers.UUIDField().run_validation(self.request.query_params['batch'])
            rows = rows.filter(batch_id=batch_id)
        status = self.request.query_params.get('status')
        return rows.filter(status=status) if status else rows

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        return Response(self.get_serializer(services.revoke(self.get_object(), request)).data)

    @action(detail=True, methods=['post'])
    def reveal(self, request, pk=None):
        voucher = self.get_object()
        AuditService.log(request=request, organization=self.get_organization(), action='hotspot.voucher_revealed',
                         resource_type='Voucher', resource_id=voucher.pk)
        response = Response({'id': str(voucher.pk), 'code': voucher.code, 'plan': voucher.plan_name,
                             'price': voucher.price, 'duration_seconds': voucher.duration_seconds})
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['post'])
    def sale(self, request, pk=None):
        with transaction.atomic():
            voucher = Voucher.objects.select_for_update().get(pk=self.get_object().pk)
            if voucher.status == 'revoked':
                raise serializers.ValidationError('Cannot sell a revoked voucher.')
            if HotspotSale.objects.filter(voucher=voucher).exists():
                raise serializers.ValidationError('Sale already recorded.')
            sale = HotspotSale.objects.create(voucher=voucher, organization=self.get_organization(), amount=voucher.price, method='cash')
            AuditService.log(request=request, organization=self.get_organization(), action='hotspot.cash_sale', resource_type='HotspotSale', resource_id=sale.pk,
                             metadata={'voucher_id': str(voucher.pk), 'amount': str(sale.amount)})
        return Response({'id': sale.pk, 'amount': sale.amount, 'method': sale.method}, status=201)


class BatchInput(serializers.Serializer):
    plan_id = serializers.IntegerField(min_value=1)
    count = serializers.IntegerField(min_value=1, max_value=200)
    label = serializers.CharField(max_length=100, required=False, allow_blank=True)
    redeem_before = serializers.DateTimeField(required=False, allow_null=True)
    def validate_redeem_before(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError('Use a future redemption deadline.')
        return value


class BatchSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source='vouchers.count', read_only=True)
    class Meta:
        model = VoucherBatch
        fields = ['id', 'plan', 'label', 'created_at', 'count']


class BatchViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = VoucherBatch.objects.select_related('plan').prefetch_related('vouchers')
    serializer_class = BatchSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'create': BILLING_ROLES, 'export': BILLING_ROLES}

    def create(self, request):
        data = BatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        attrs = dict(data.validated_data)
        plan = get_object_or_404(HotspotPlan, pk=attrs.pop('plan_id'), organization=self.get_organization())
        batch = services.issue_batch(plan, **attrs)
        AuditService.log(request=request, organization=self.get_organization(), action='hotspot.batch_created', resource_type='VoucherBatch', resource_id=batch.pk,
                         metadata={'count': data.validated_data['count']})
        return Response(BatchSerializer(batch).data, status=201)

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        batch = self.get_object()
        AuditService.log(request=request, organization=self.get_organization(), action='hotspot.vouchers_exported', resource_type='VoucherBatch', resource_id=batch.pk)
        response = Response({'batch': str(batch.pk), 'vouchers': [{'id': str(v.pk), 'code': v.code, 'plan': v.plan_name,
                             'price': v.price, 'duration_seconds': v.duration_seconds} for v in batch.vouchers.all()]})
        response['Cache-Control'] = 'no-store'
        return response


class SessionSerializer(serializers.ModelSerializer):
    nas_name = serializers.CharField(source='nas.name')
    stale = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField()
    class Meta:
        model = HotspotSession
        fields = ['id', 'voucher', 'nas', 'nas_name', 'session_id', 'mac', 'ip', 'started_at', 'updated_at', 'stopped_at', 'disconnected_at',
                  'duration_seconds', 'upload_bytes', 'download_bytes', 'terminate_cause', 'stale', 'online']
    def get_stale(self, obj):
        return not obj.stopped_at and not obj.disconnected_at and obj.updated_at < timezone.now()-timedelta(seconds=180)
    def get_online(self, obj):
        return bool(obj.started_at and not obj.stopped_at and not obj.disconnected_at and not self.get_stale(obj))


class SessionViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    organization_field = 'voucher__organization'
    queryset = HotspotSession.objects.select_related('nas', 'voucher')
    serializer_class = SessionSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'disconnect': NETWORK_ROLES}
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        from radius.disconnect import queue_disconnect
        session = self.get_object()
        item = queue_disconnect(session.nas, session.voucher.code, session.session_id, session.mac, 'operator', request)
        return Response({'request_id': item.pk, 'status': item.status}, status=202)


class Summary(APIView):
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'get': READ_ONLY_ROLES}
    def get(self, request):
        from organizations.services import get_user_organization
        org = get_user_organization(request.user)
        sessions = HotspotSession.objects.filter(voucher__organization=org)
        receipts = HotspotSale.objects.filter(organization=org)
        from django.conf import settings
        return Response({'aaa_mode': 'registered_nas' if settings.RADIUS_ISOLATED else 'legacy', 'plans': HotspotPlan.objects.filter(organization=org, is_active=True).count(),
            'vouchers': Voucher.objects.filter(organization=org).count(),
            'online_sessions': sessions.filter(stopped_at__isnull=True, disconnected_at__isnull=True, started_at__isnull=False,
                                              updated_at__gte=timezone.now()-timedelta(seconds=180)).count(),
            'received': float(receipts.aggregate(total=Sum('amount'))['total'] or 0),
            'upload_bytes': sessions.aggregate(total=Sum('upload_bytes'))['total'] or 0,
            'download_bytes': sessions.aggregate(total=Sum('download_bytes'))['total'] or 0})


class PurchaseThrottle(AnonRateThrottle):
    rate = '300/hour'
    scope = 'hotspot-purchase'


class PublicPurchase(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PurchaseThrottle]
    def finalize_response(self, request, response, *args, **kwargs):
        response['Cache-Control'] = 'no-store'
        return super().finalize_response(request, response, *args, **kwargs)
    def nas(self, public_id):
        return get_object_or_404(NasDevice, public_id=public_id, is_active=True, hotspot_enabled=True,
                                organization__is_active=True, organization__status='active')
    def get_throttles(self):
        return [PublicReadThrottle()] if self.request.method == 'GET' else [PurchaseThrottle()]
    def get(self, request, public_id):
        nas = self.nas(public_id)
        from django.conf import settings
        from payments.models import MpesaConfiguration
        enabled = bool(settings.RADIUS_ISOLATED and len(settings.RADIUS_INTERNAL_TOKEN) >= 32 and settings.PUBLIC_BASE_URL.startswith('https://') and MpesaConfiguration.objects.filter(organization=nas.organization, is_active=True, is_default=True, service_scope__in=['hotspot','both']).exists())
        return Response({'isp': nas.organization.name, 'purchases_enabled': enabled, 'plans': PlanSerializer(HotspotPlan.objects.filter(organization=nas.organization, is_active=True), many=True).data})
    def post(self, request, public_id):
        from .payments import start_purchase
        nas = self.nas(public_id)
        plan_id = serializers.IntegerField(min_value=1).run_validation(request.data.get('plan_id'))
        phone = serializers.RegexField(r'^(?:254|0)[17]\d{8}$').run_validation(request.data.get('phone_number'))
        plan = get_object_or_404(HotspotPlan, pk=plan_id, organization=nas.organization, is_active=True)
        request_id = serializers.UUIDField().run_validation(request.data.get("request_id"))
        purchase, token = start_purchase(nas, plan, phone, request_id)
        return Response({'purchase_id': str(purchase.pk), 'purchase_token': token, 'status': purchase.initiation_status}, status=202)


class PublicReadThrottle(AnonRateThrottle):
    rate = '600/minute'
    scope = 'hotspot-public-read'


class PurchaseStatus(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicReadThrottle]
    def post(self, request):
        token = serializers.CharField(min_length=40, max_length=100).run_validation(request.data.get('purchase_token'))
        purchase = get_object_or_404(HotspotPurchase.objects.select_related('attempt', 'voucher'), token_hash=services.digest(token))
        status = purchase.attempt.status if purchase.attempt else 'failed'
        response = Response({'status': status, 'fulfilled': bool(purchase.voucher_id),
                             'voucher_code': purchase.voucher.code if purchase.voucher_id else None})
        response['Cache-Control'] = 'no-store'
        return response


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotspotSale
        fields = ['id', 'voucher', 'amount', 'method', 'receipt', 'created_at']


class SaleViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = HotspotSale.objects.order_by('-created_at', '-id')
    serializer_class = SaleSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': BILLING_ROLES}


class PurchaseSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    settlement = serializers.SerializerMethodField()
    receipt = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    class Meta:
        model = HotspotPurchase
        fields = ['id', 'nas', 'plan', 'price', 'initiation_status', 'status', 'settlement', 'receipt', 'phone', 'voucher', 'created_at']
    def get_status(self, obj): return obj.attempt.status if obj.attempt else 'unconfirmed'
    def get_settlement(self, obj): return obj.attempt.settlement_status if obj.attempt else 'unsettled'
    def get_receipt(self, obj): return obj.attempt.mpesa_receipt_number if obj.attempt else None
    def get_phone(self, obj): return '••••' + obj.attempt.phone_number[-4:] if obj.attempt else '—'


class PurchaseViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    organization_field = 'nas__organization'
    queryset = HotspotPurchase.objects.select_related('attempt', 'voucher').order_by('-created_at', '-id')
    serializer_class = PurchaseSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': BILLING_ROLES, 'reconcile': BILLING_ROLES}
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        from payments.services.reconciliation import PaymentReconciliationService
        from .payments import finalize_purchase
        purchase = self.get_object()
        if not purchase.attempt or not purchase.attempt.checkout_request_id:
            raise serializers.ValidationError('Provider submission is unconfirmed. Verify with the ISP payment provider before requesting another payment.')
        try:
            PaymentReconciliationService.reconcile_attempt(purchase.attempt_id)
            purchase.attempt.refresh_from_db()
            if purchase.attempt.status == 'successful':
                finalize_purchase(purchase.attempt_id)
        except Exception:
            raise serializers.ValidationError('Payment cannot yet be confirmed or fulfilled. Check for a callback and provider receipt; do not charge again.') from None
        purchase.refresh_from_db()
        AuditService.log(request=request, organization=self.get_organization(), action='hotspot.payment_reconciled',
                         resource_type='HotspotPurchase', resource_id=purchase.pk)
        return Response(self.get_serializer(purchase).data)
