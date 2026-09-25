from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import select

from app.extensions import db
from app.models.admin_user import AdminUser


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/v1/auth",
)


# FIRST ADMIN REGISTRATION
@auth_bp.post("/register")
def register():
    existing_admin = db.session.scalar(
        select(AdminUser).limit(1)
    )

    if existing_admin is not None:
        return {
            "status": "error",
            "message": "Administrator already exists.",
        }, 409

    data = request.get_json(silent=True) or {}

    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not full_name or not email or not password:
        return {
            "status": "error",
            "message": "Full name, email and password are required.",
        }, 400

    if len(password) < 8:
        return {
            "status": "error",
            "message": "Password must be at least 8 characters.",
        }, 400

    admin = AdminUser(
        full_name=full_name,
        email=email,
        role="super_admin",
        is_active=True,
    )

    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    return {
        "status": "success",
        "message": "Administrator registered successfully.",
        "data": {
            "user": {
                "id": admin.id,
                "full_name": admin.full_name,
                "email": admin.email,
                "role": admin.role,
            }
        },
    }, 201


# LOGIN
@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return {
            "status": "error",
            "message": "Email and password are required.",
        }, 400

    user = db.session.scalar(
        select(AdminUser).where(
            AdminUser.email == email
        )
    )

    if user is None or not user.check_password(password):
        return {
            "status": "error",
            "message": "Invalid email or password.",
        }, 401

    if not user.is_active:
        return {
            "status": "error",
            "message": "Account is disabled.",
        }, 403

    user.last_login_at = datetime.now(timezone.utc)

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
        },
    )

    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
        },
    )

    db.session.commit()

    return {
        "status": "success",
        "message": "Login successful.",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "organization" : (
                    {
                        
                        "id": user.organization.id,
                        "name": user.organization.name,
                        "slug": user.organization.slug,
                    }
                    if user.organization
                    else None
                ),
            },
        },
    }, 200


# CURRENT LOGGED-IN ADMIN
@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()

    user = db.session.get(
        AdminUser,
        int(user_id),
    )

    if user is None:
        return {
            "status": "error",
            "message": "User not found.",
        }, 404

    return {
        "status": "success",
        "data": {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            }
        },
    }, 200


# REFRESH ACCESS TOKEN
@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()

    user = db.session.get(
        AdminUser,
        int(user_id),
    )

    if user is None or not user.is_active:
        return {
            "status": "error",
            "message": "User unavailable.",
        }, 401

    new_access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
        },
    )

    return {
        "status": "success",
        "data": {
            "access_token": new_access_token,
        },
    }, 200