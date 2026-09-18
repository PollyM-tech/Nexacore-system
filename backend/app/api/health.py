from flask import Blueprint, current_app
from sqlalchemy import text

from app.extensions import db


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


@health_bp.get("/health/db")
def database_health():
    try:
        db.session.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected",
        }, 200

    except Exception:
        current_app.logger.exception(
            "Database health check failed"
        )

        return {
            "status": "error",
            "database": "unavailable",
        }, 503