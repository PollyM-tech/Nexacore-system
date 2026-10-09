from django.urls import path

from .views import StkCallbackView


urlpatterns = [
    path(
        "hooks/stk/<uuid:callback_token>/result/",
        StkCallbackView.as_view(),
        name="stk-callback",
    ),
]