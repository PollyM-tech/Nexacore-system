from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlog.models import AuditLog
from auditlog.services import AuditService
from billing.models import Package
from core.pagination import CustomPagination
from customers.models import CustomerProfile
from mikrotik.models import MikrotikRouter
from organizations.models import Organization, OrganizationMembership
from .permissions import IsPlatformAdmin
from .serializers import (
    IdentitySerializer, MembershipSerializer, OrganizationSerializer,
    PlatformAuditSerializer, PlatformUserSerializer,
)


def usage_count(model):
    query = model.objects.filter(organization_id=OuterRef("pk")).order_by().values("organization_id").annotate(n=Count("pk")).values("n")
    return Coalesce(Subquery(query, output_field=IntegerField()), Value(0))


def organizations():
    return Organization.objects.annotate(
        member_count=usage_count(OrganizationMembership),
        customer_count=usage_count(CustomerProfile),
        router_count=usage_count(MikrotikRouter),
        package_count=usage_count(Package),
    ).order_by("name", "pk")


def audit(request, action, instance, organization, metadata=None):
    AuditService.log(request=request, action=action, organization=organization,
                     resource_type=type(instance).__name__, resource_id=instance.pk, metadata=metadata)


class PlatformMe(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        return Response({"is_platform_admin": True, "user": IdentitySerializer(request.user).data})


class OrganizationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = OrganizationSerializer
    pagination_class = CustomPagination
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "is_active"]
    search_fields = ["name", "slug"]

    def get_queryset(self):
        return organizations()

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save()
        audit(self.request, "platform.organization_created", instance, instance)
        serializer.instance = organizations().get(pk=instance.pk)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = Organization.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.instance = instance
        instance = serializer.save()
        audit(self.request, "platform.organization_updated", instance, instance,
              {"changed_fields": list(serializer.validated_data)})
        serializer.instance = organizations().get(pk=instance.pk)


class MembershipViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = MembershipSerializer
    pagination_class = CustomPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        get_object_or_404(Organization, pk=self.kwargs["org_id"])
        return OrganizationMembership.objects.filter(organization_id=self.kwargs["org_id"]).select_related("user").order_by("pk")

    def locked_organization(self):
        # All platform membership mutations serialize on the parent row, even
        # when two different owner memberships are edited concurrently.
        return get_object_or_404(Organization.objects.select_for_update(), pk=self.kwargs["org_id"])

    @staticmethod
    def protect_owner(instance, attrs=None):
        attrs = attrs or {}
        losing_owner = attrs.get("role", instance.role) != "owner" or not attrs.get("is_active", instance.is_active)
        if instance.role == "owner" and instance.is_active and instance.user.is_active and losing_owner:
            if not OrganizationMembership.objects.filter(
                organization=instance.organization, role="owner", is_active=True, user__is_active=True,
            ).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError({"role": "The last active owner cannot be removed, disabled or demoted. Add another active owner first."})

    @transaction.atomic
    def perform_create(self, serializer):
        org = self.locked_organization()
        user = serializer.validated_data["user"]
        if OrganizationMembership.objects.filter(organization=org, user=user).exists():
            raise serializers.ValidationError({"user_id": "This user is already a member of this organization."})
        try:
            with transaction.atomic():
                instance = serializer.save(organization=org)
        except IntegrityError:
            raise serializers.ValidationError({"user_id": "Membership could not be created. Check whether the user is already assigned."}) from None
        audit(self.request, "platform.membership_created", instance, org, {"user_id": user.pk, "role": instance.role})

    @transaction.atomic
    def perform_update(self, serializer):
        org = self.locked_organization()
        instance = get_object_or_404(OrganizationMembership.objects.select_related("user"), pk=serializer.instance.pk, organization=org)
        self.protect_owner(instance, serializer.validated_data)
        serializer.instance = instance
        instance = serializer.save()
        audit(self.request, "platform.membership_updated", instance, org,
              {"user_id": instance.user_id, "role": instance.role, "is_active": instance.is_active})

    @transaction.atomic
    def perform_destroy(self, instance):
        org = self.locked_organization()
        instance = get_object_or_404(OrganizationMembership.objects.select_related("user"), pk=instance.pk, organization=org)
        self.protect_owner(instance, {"is_active": False})
        audit(self.request, "platform.membership_removed", instance, org, {"user_id": instance.user_id})
        instance.delete()


class PlatformSummary(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        def totals(model, active):
            return model.objects.aggregate(total=Count("pk"), active=Count("pk", filter=active))
        return Response({
            "organizations": totals(Organization, Q(is_active=True, status="active")),
            "users": {"total": get_user_model().objects.count()},
            "customers": totals(CustomerProfile, Q(customer_status="active")),
            "routers": totals(MikrotikRouter, Q(is_active=True)),
            "packages": totals(Package, Q(is_active=True)),
        })


class PlatformUsers(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformUserSerializer
    pagination_class = CustomPagination
    queryset = get_user_model().objects.annotate(membership_count=Count("organization_memberships")).order_by("pk")
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "email", "first_name", "last_name"]


class PlatformAudit(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PlatformAuditSerializer
    pagination_class = CustomPagination
    queryset = AuditLog.objects.select_related("user", "organization").order_by("-created_at", "-pk")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["organization", "user", "action"]
