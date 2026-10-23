from django.urls import path

from rest_framework.routers import DefaultRouter
from .nas_api import NasViewSet, DisconnectViewSet
from radius.views import RadiusSessionViewSet

router = DefaultRouter()
router.register("nas", NasViewSet)
router.register("disconnects", DisconnectViewSet)


session_list = (
    RadiusSessionViewSet.as_view(
        {
            "get": "list",
        }
    )
)

active_sessions = (
    RadiusSessionViewSet.as_view(
        {
            "get": "active",
        }
    )
)

customer_sessions = (
    RadiusSessionViewSet.as_view(
        {
            "get": "customer_sessions",
        }
    )
)

customer_summary = (
    RadiusSessionViewSet.as_view(
        {
            "get": "customer_summary",
        }
    )
)


urlpatterns = router.urls + [
    path(
        "sessions/",
        session_list,
        name="radius-session-list",
    ),
    path(
        "sessions/active/",
        active_sessions,
        name="radius-active-sessions",
    ),
    path(
        "customers/<str:customer_id>/sessions/",
        customer_sessions,
        name="radius-customer-sessions",
    ),
    path(
        "customers/<str:customer_id>/summary/",
        customer_summary,
        name="radius-customer-summary",
    ),
]