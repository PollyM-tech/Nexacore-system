from functools import wraps

from flask_jwt_extended import get_jwt, jwt_required


def super_admin_required():
    def decorator(function):
        @wraps(function)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()

            if claims.get("role") != "super_admin":
                return {
                    "status": "error",
                    "message": "Super administrator access required.",
                }, 403

            return function(*args, **kwargs)

        return wrapper

    return decorator