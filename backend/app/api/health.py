from flask import Blueprint


health_bp = Blueprint(
    "health",
    __name__,
    url_prefix="/api/v1",
)


@health_bp.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nexacore-api",
    }, 200