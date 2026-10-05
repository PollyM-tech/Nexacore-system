from dataclasses import dataclass, field
from typing import Callable, Dict, List


@dataclass
class RequestSpec:
    """
    Describes one HTTP request to an SMS provider.
    """

    url: str
    method: str = "get"
    params: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)
    json: dict | None = None
    headers: dict = field(default_factory=dict)


REGISTRY: Dict[str, dict] = {}


def f(
    key: str,
    label: str,
    secret: bool = False,
    required: bool = True,
) -> dict:
    """
    Credential-field descriptor used by the API/UI.
    """

    return {
        "key": key,
        "label": label,
        "secret": secret,
        "required": required,
    }


def register(
    key: str,
    label: str,
    fields: List[dict],
):
    """
    Register an SMS provider in the provider registry.
    """

    def decorator(
        builder: Callable[
            [dict, str, str],
            RequestSpec,
        ]
    ):
        REGISTRY[key] = {
            "key": key,
            "label": label,
            "fields": fields,
            "builder": builder,
        }

        return builder

    return decorator


def build_spec(
    provider: str,
    creds: dict,
    mobile: str,
    message: str,
) -> RequestSpec:
    """
    Build the HTTP request definition for a provider.
    """

    entry = REGISTRY.get(
        provider
    )

    if not entry:
        raise ValueError(
            f"Unknown SMS provider "
            f"'{provider}'."
        )

    return entry["builder"](
        creds,
        mobile,
        message,
    )


def provider_metadata() -> List[dict]:
    """
    Return public provider configuration metadata.

    Secret values themselves are never returned here.
    """

    return [
        {
            "key": entry["key"],
            "label": entry["label"],
            "fields": entry["fields"],
        }
        for entry in sorted(
            REGISTRY.values(),
            key=lambda item: (
                item["label"].lower()
            ),
        )
    ]