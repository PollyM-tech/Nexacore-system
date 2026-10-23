import ipaddress
from django.conf import settings
from django.db import transaction
from rest_framework import serializers, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.pagination import CustomPagination
from organizations.mixins import OrganizationQuerySetMixin
from organizations.permissions import HasOrganizationRole, READ_ONLY_ROLES, NETWORK_ROLES, ADMIN_ROLES
from auditlog.services import AuditService
from .models import NasDevice, DisconnectRequest


class NasSerializer(serializers.ModelSerializer):
    create_pppoe_router = serializers.BooleanField(write_only=True, required=False, default=False)
    shared_secret = serializers.CharField(write_only=True, required=True, min_length=32, max_length=128, trim_whitespace=False)

    class Meta:
        model = NasDevice
        fields = ['id', 'public_id', 'create_pppoe_router', 'name', 'source_ip', 'identifier', 'shared_secret', 'router', 'disconnect_port', 'is_active', 'hotspot_enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'public_id', 'created_at', 'updated_at']

    def validate_shared_secret(self, value):
        if any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise serializers.ValidationError('Use 32–128 printable ASCII characters without spaces.')
        return value

    def validate(self, attrs):
        org = self.context['view'].get_organization()
        router = attrs.get('router', self.instance.router if self.instance else None)
        if attrs.get('create_pppoe_router') and (self.instance or router):
            raise serializers.ValidationError('Choose either an existing router or a new RADIUS-only router when registering a NAS.')
        if router and router.organization_id != org.pk:
            raise serializers.ValidationError({'router': 'Router must belong to your organization.'})
        ip = attrs.get('source_ip', self.instance.source_ip if self.instance else None)
        network = ipaddress.ip_network(getattr(settings, 'RADIUS_NAS_NETWORK', '10.64.0.0/16'))
        if ipaddress.ip_address(ip) not in network:
            raise serializers.ValidationError({'source_ip': 'Use a unique source address in the platform-approved NAS/VPN network.'})
        port = attrs.get('disconnect_port', self.instance.disconnect_port if self.instance else 3799)
        if not 1024 <= port <= 65535:
            raise serializers.ValidationError({'disconnect_port': 'Use a port from 1024 to 65535.'})
        # Source identity and tenant attachment are immutable; add a new NAS for migration.
        if self.instance and any(k in attrs and attrs[k] != getattr(self.instance, k) for k in ('source_ip', 'router')):
            raise serializers.ValidationError('NAS source address and router attachment cannot be changed in place.')
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from mikrotik.models import MikrotikRouter
        if validated_data.pop('create_pppoe_router', False):
            validated_data['router'] = MikrotikRouter.objects.create(
                organization=validated_data['organization'], name=validated_data['name'],
                host=validated_data['source_ip'], username='', password='',
                description='RADIUS-only NAS. RouterOS API credentials are not configured.')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('create_pppoe_router', None)
        return super().update(instance, validated_data)


class NasViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                 mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = NasDevice.objects.select_related('organization', 'router')
    serializer_class = NasSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'retrieve': READ_ONLY_ROLES, 'create': ADMIN_ROLES,
                        'update': ADMIN_ROLES, 'partial_update': ADMIN_ROLES, 'captive_template': NETWORK_ROLES}

    @action(detail=True, methods=['get'], url_path='captive-template')
    def captive_template(self, request, pk=None):
        from pathlib import Path
        from html import escape
        from django.http import HttpResponse
        nas = self.get_object()
        base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
        if not base.startswith('https://'):
            raise serializers.ValidationError('Configure the public HTTPS base URL before downloading a customer-facing portal template.')
        template = (Path(settings.BASE_DIR) / 'hotspot/templates/mikrotik/login.html').read_text()
        response = HttpResponse(template.replace('__PURCHASE_URL__', escape(f'{base}/hotspot/{nas.public_id}', quote=True)), content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="login.html"'
        response['Cache-Control'] = 'no-store'
        return response

    def perform_create(self, serializer):
        obj = serializer.save(organization=self.get_organization())
        AuditService.log(request=self.request, organization=obj.organization, action='radius.nas_created', resource_type='NasDevice', resource_id=obj.pk)

    def perform_update(self, serializer):
        obj = serializer.save()
        AuditService.log(request=self.request, organization=obj.organization, action='radius.nas_updated', resource_type='NasDevice', resource_id=obj.pk,
                         metadata={'fields': [k for k in serializer.validated_data if k != 'shared_secret'], 'secret_changed': 'shared_secret' in serializer.validated_data})


class DisconnectSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()

    class Meta:
        model = DisconnectRequest
        fields = ['id', 'nas', 'session_id', 'reason', 'status', 'attempts', 'max_attempts', 'next_attempt_at', 'last_error', 'acknowledged_at', 'created_at', 'events']

    def get_events(self, obj):
        return [{'number': e.number, 'result': e.result, 'error_cause': e.error_cause, 'created_at': e.created_at} for e in obj.events.all()]


class DisconnectViewSet(OrganizationQuerySetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    organization_field = 'nas__organization'
    queryset = DisconnectRequest.objects.select_related('nas').prefetch_related('events')
    serializer_class = DisconnectSerializer
    permission_classes = [IsAuthenticated, HasOrganizationRole]
    role_permissions = {'list': READ_ONLY_ROLES, 'retrieve': READ_ONLY_ROLES, 'retry': NETWORK_ROLES}
    pagination_class = CustomPagination

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        from django.db import transaction
        from django.utils import timezone
        with transaction.atomic():
            obj = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
            if obj.status not in ('failed', 'retry'):
                raise serializers.ValidationError('Only failed/retry requests can be retried.')
            if obj.status == 'failed':
                obj.max_attempts = obj.attempts + 5
            AuditService.log(request=request, organization=obj.nas.organization, action='radius.disconnect_retry_requested',
                resource_type='DisconnectRequest', resource_id=obj.pk, metadata={'attempts': obj.attempts, 'max_attempts': obj.max_attempts})
            obj.status, obj.next_attempt_at = 'pending', timezone.now()
            obj.save(update_fields=['status', 'next_attempt_at', 'max_attempts'])
        return Response(self.get_serializer(obj).data)
