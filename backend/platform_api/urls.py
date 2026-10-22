from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import MembershipViewSet, OrganizationViewSet, PlatformAudit, PlatformMe, PlatformSummary, PlatformUsers

router = DefaultRouter()
# DefaultRouter discovery views inherit global permissions, not our viewsets.
# Do not publish an unguarded platform API root.
router.include_root_view = False
router.register("organizations", OrganizationViewSet, basename="platform-organizations")
router.register("users", PlatformUsers, basename="platform-users")
router.register("audit", PlatformAudit, basename="platform-audit")
members = MembershipViewSet.as_view({"get": "list", "post": "create"})
member = MembershipViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})
urlpatterns = [
    path("me/", PlatformMe.as_view(), name="platform-me"),
    path("summary/", PlatformSummary.as_view(), name="platform-summary"),
    path("organizations/<int:org_id>/members/", members, name="platform-members"),
    path("organizations/<int:org_id>/members/<int:pk>/", member, name="platform-member"),
    path("", include(router.urls)),
]
