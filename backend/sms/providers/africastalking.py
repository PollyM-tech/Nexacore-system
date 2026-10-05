from .base import RequestSpec, f, register


@register(
    "africastalking",
    "Africa's Talking",
    [
        f("username", "Username"),
        f("api_key", "API key", secret=True),
        f(
            "environment",
            "Environment (sandbox/live)",
            required=False,
        ),
    ],
)
def africastalking(c, mobile, message):
    environment = (
        c.get("environment")
        or "sandbox"
    ).lower()

    if environment == "live":
        url = (
            "https://api.africastalking.com/"
            "version1/messaging"
        )
    else:
        url = (
            "https://api.sandbox.africastalking.com/"
            "version1/messaging"
        )

    payload = {
        "username": c["username"],
        "to": mobile,
        "message": message,
    }

    sender_id = c.get("sender_id")

    if sender_id:
        payload["from"] = sender_id

    return RequestSpec(
        url=url,
        method="post",
        headers={
            "apiKey": c["api_key"],
            "Accept": "application/json",
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
        },
        data=payload,
    )