from django.urls import path

from radius.views import RadiusSessionViewSet


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


urlpatterns = [
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