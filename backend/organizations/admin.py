from django.contrib import admin

from .models import Organization, OrganizationMembership


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "organization_type",
        "status",
        "country",
        "currency",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "name",
        "slug",
        "email",
        "phone_number",
    ]

    list_filter = [
        "organization_type",
        "status",
        "is_active",
    ]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "organization",
        "role",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "role",
        "is_active",
        "organization",
    ]

    search_fields = [
        "user__username",
        "user__email",
        "organization__name",
    ]