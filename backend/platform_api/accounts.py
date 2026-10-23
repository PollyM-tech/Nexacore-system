"""Explicit superadmin-led staff provisioning; never public registration."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlog.services import AuditService
from organizations.models import Organization, OrganizationMembership
from .permissions import IsPlatformAdmin
from .serializers import MembershipSerializer


class NewStaffSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=255)
    role = serializers.ChoiceField(choices=OrganizationMembership.ROLE_CHOICES)

    def validate(self, attrs):
        User = get_user_model()
        attrs["email"] = attrs["email"].lower()
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "An account already uses this email. Add its existing membership instead."})
        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "This username is already in use."})
        user = User(**{key: value for key, value in attrs.items() if key not in ("password", "role")})
        try:
            validate_password(attrs["password"], user=user)
            user.full_clean(exclude=["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"account": exc.messages}) from None
        return attrs


class OrganizationStaffCreate(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, org_id):
        serializer = NewStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = dict(serializer.validated_data)
        role = attrs.pop("role")
        try:
            with transaction.atomic():
                # Serialize provisioning across organizations; email is not unique on Django User.
                get_user_model().objects.select_for_update().order_by("pk").first()
                if get_user_model().objects.filter(email__iexact=attrs["email"]).exists():
                    raise serializers.ValidationError({"email": "An account already uses this email."})
                organization = get_object_or_404(Organization.objects.select_for_update(), pk=org_id, is_active=True)
                user = get_user_model().objects.create_user(**attrs, is_staff=False, is_superuser=False)
                membership = OrganizationMembership.objects.create(organization=organization, user=user, role=role)
                AuditService.log(request=request, organization=organization, action="platform.staff_created",
                                 resource_type="User", resource_id=user.pk, metadata={"user_id": user.pk, "role": role})
        except IntegrityError:
            raise serializers.ValidationError({"account": "Account could not be created. Check for a duplicate username or email."}) from None
        return Response(MembershipSerializer(membership).data, status=201)
