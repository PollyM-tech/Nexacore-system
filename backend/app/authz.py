from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models.admin_user import AdminUser


def get_current_user():
    """
    Get the currently authenticated administrator.

    The JWT provides the user ID.
    The database provides the user's current:
    - role
    - organization
    - active status
    """

    identity = get_jwt_identity()

    if identity is None:
        return None

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.get(AdminUser, user_id)


def super_admin_required():
    def decorator(function):
        @wraps(function)
        @jwt_required()
        def wrapper(*args, **kwargs):

            user = get_current_user()

            if user is None:
                return {
                    "status": "error",
                    "message": "Authenticated user not found.",
                }, 401

            if not user.is_active:
                return {
                    "status": "error",
                    "message": "Account is disabled.",
                }, 403

            if user.role != "super_admin":
                return {
                    "status": "error",
                    "message": "Super administrator access required.",
                }, 403

            return function(*args, **kwargs)

        return wrapper

    return decorator


def organization_admin_required():
    def decorator(function):
        @wraps(function)
        @jwt_required()
        def wrapper(*args, **kwargs):

            user = get_current_user()

            if user is None:
                return {
                    "status": "error",
                    "message": "Authenticated user not found.",
                }, 401

            if not user.is_active:
                return {
                    "status": "error",
                    "message": "Account is disabled.",
                }, 403

            if user.role != "organization_admin":
                return {
                    "status": "error",
                    "message": "Organization administrator access required.",
                }, 403

            if user.organization_id is None:
                return {
                    "status": "error",
                    "message": "User is not assigned to an organization.",
                }, 403

            return function(*args, **kwargs)

        return wrapper

    return decorator


def admin_required():
    def decorator(function):
        @wraps(function)
        @jwt_required()
        def wrapper(*args, **kwargs):

            user = get_current_user()

            if user is None:
                return {
                    "status": "error",
                    "message": "Authenticated user not found.",
                }, 401

            if not user.is_active:
                return {
                    "status": "error",
                    "message": "Account is disabled.",
                }, 403

            if user.role not in {
                "super_admin",
                "organization_admin",
            }:
                return {
                    "status": "error",
                    "message": "Administrator access required.",
                }, 403

            return function(*args, **kwargs)

        return wrapper

    return decorator