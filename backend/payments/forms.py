from django import forms

from .models import MpesaConfiguration


class MpesaConfigurationAdminForm(forms.ModelForm):
    """
    Internal Lintech form for configuring an ISP's Daraja integration.

    Existing secrets are never rendered back into the browser.
    Leaving a secret field blank while editing preserves the stored value.
    """

    consumer_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "autocomplete": "new-password",
            },
        ),
    )

    consumer_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "autocomplete": "new-password",
            },
        ),
    )

    passkey = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "autocomplete": "new-password",
            },
        ),
    )

    class Meta:
        model = MpesaConfiguration
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        payment_mode = cleaned_data.get("payment_mode")
        shortcode = (cleaned_data.get("shortcode") or "").strip()

        consumer_key = cleaned_data.get("consumer_key") or ""
        consumer_secret = cleaned_data.get("consumer_secret") or ""
        passkey = cleaned_data.get("passkey") or ""

        if self.instance and self.instance.pk:
            if not consumer_key:
                consumer_key = self.instance.consumer_key

            if not consumer_secret:
                consumer_secret = self.instance.consumer_secret

            if not passkey:
                passkey = self.instance.passkey

        if payment_mode == "own_shortcode":
            errors = {}

            if not shortcode:
                errors["shortcode"] = (
                    "Shortcode is required for ISP-owned M-Pesa."
                )

            if not consumer_key:
                errors["consumer_key"] = (
                    "Consumer Key is required."
                )

            if not consumer_secret:
                errors["consumer_secret"] = (
                    "Consumer Secret is required."
                )

            if not passkey:
                errors["passkey"] = (
                    "Daraja passkey is required."
                )

            if errors:
                raise forms.ValidationError(errors)

        cleaned_data["shortcode"] = shortcode
        cleaned_data["consumer_key"] = consumer_key
        cleaned_data["consumer_secret"] = consumer_secret
        cleaned_data["passkey"] = passkey

        return cleaned_data