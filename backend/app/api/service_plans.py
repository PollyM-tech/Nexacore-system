from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_, select

from app.extensions import db
from app.models.admin_user import AdminUser
from app.models.service_plan import ServicePlan


service_plans_bp = Blueprint(
    "service_plans",
    __name__,
    url_prefix="/api/v1/service-plans",
)


ALLOWED_SERVICE_TYPES = {
    "pppoe",
    "hotspot",
    "static",
}

ALLOWED_BILLING_PERIODS = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "yearly",
}

ALLOWED_STATUSES = {
    "active",
    "inactive",
}


def get_current_user():
    """
    Return the authenticated AdminUser.

    The JWT identity is expected to contain the admin user's ID.
    """
    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return db.session.get(AdminUser, user_id)


def error_response(message, status_code=400):
    return {
        "status": "error",
        "message": message,
    }, status_code


def success_response(data=None, message=None, status_code=200):
    response = {
        "status": "success",
    }

    if message is not None:
        response["message"] = message

    if data is not None:
        response["data"] = data

    return response, status_code


def validate_price(value):
    """
    Validate and normalize a plan price.

    Returns:
        Decimal value or None if invalid.
    """
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    if price < Decimal("0"):
        return None

    return price.quantize(Decimal("0.01"))


def validate_positive_integer(value, field_name):
    """
    Validate optional positive integer fields such as:
    - speed
    - data limit
    - validity days
    """
    if value is None:
        return None, None

    if isinstance(value, bool):
        return None, f"{field_name} must be a positive integer."

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be a positive integer."

    if parsed <= 0:
        return None, f"{field_name} must be greater than zero."

    return parsed, None


def get_organization_id(user):
    """
    Return the organization ID for an organization administrator.

    Super administrators currently do not receive an organization ID
    from the user record, so they must explicitly provide an organization
    context when working with organization-owned service plans.
    """
    if user is None:
        return None

    return user.organization_id


@service_plans_bp.get("")
@jwt_required()
def list_service_plans():
    """
    List service plans belonging to the authenticated organization.

    Supported query parameters:

    page
    per_page
    search
    service_type
    status
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return error_response(
            "page and per_page must be valid integers.",
            400,
        )

    per_page = min(max(per_page, 1), 100)

    search = request.args.get("search", "").strip()
    service_type = request.args.get("service_type", "").strip().lower()
    status = request.args.get("status", "").strip().lower()

    statement = select(ServicePlan).where(
        ServicePlan.organization_id == organization_id
    )

    if search:
        pattern = f"%{search}%"

        statement = statement.where(
            or_(
                ServicePlan.name.ilike(pattern),
                ServicePlan.description.ilike(pattern),
            )
        )

    if service_type:
        if service_type not in ALLOWED_SERVICE_TYPES:
            return error_response(
                "Invalid service_type.",
                400,
            )

        statement = statement.where(
            ServicePlan.service_type == service_type
        )

    if status:
        if status not in ALLOWED_STATUSES:
            return error_response(
                "Invalid status.",
                400,
            )

        statement = statement.where(
            ServicePlan.status == status
        )

    statement = statement.order_by(
        ServicePlan.created_at.desc()
    )

    pagination = db.paginate(
        statement,
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return success_response(
        {
            "items": [
                plan.to_dict()
                for plan in pagination.items
            ],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@service_plans_bp.post("")
@jwt_required()
def create_service_plan():
    """
    Create a service plan for the authenticated organization.
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "Request body must be a JSON object.",
            400,
        )

    name = str(data.get("name", "")).strip()
    service_type = str(
        data.get("service_type", "")
    ).strip().lower()
    billing_period = str(
        data.get("billing_period", "")
    ).strip().lower()
    status = str(
        data.get("status", "active")
    ).strip().lower()

    if not name:
        return error_response(
            "Plan name is required.",
            400,
        )

    if len(name) > 150:
        return error_response(
            "Plan name cannot exceed 150 characters.",
            400,
        )

    if service_type not in ALLOWED_SERVICE_TYPES:
        return error_response(
            "service_type must be one of: pppoe, hotspot, static.",
            400,
        )

    if billing_period not in ALLOWED_BILLING_PERIODS:
        return error_response(
            "billing_period must be one of: daily, weekly, monthly, quarterly, yearly.",
            400,
        )

    if status not in ALLOWED_STATUSES:
        return error_response(
            "status must be active or inactive.",
            400,
        )

    if "price" not in data:
        return error_response(
            "Price is required.",
            400,
        )

    price = validate_price(data.get("price"))

    if price is None:
        return error_response(
            "Price must be a valid non-negative number.",
            400,
        )

    download_speed, error = validate_positive_integer(
        data.get("download_speed"),
        "download_speed",
    )

    if error:
        return error_response(error, 400)

    upload_speed, error = validate_positive_integer(
        data.get("upload_speed"),
        "upload_speed",
    )

    if error:
        return error_response(error, 400)

    data_limit, error = validate_positive_integer(
        data.get("data_limit"),
        "data_limit",
    )

    if error:
        return error_response(error, 400)

    validity_days, error = validate_positive_integer(
        data.get("validity_days"),
        "validity_days",
    )

    if error:
        return error_response(error, 400)

    description = data.get("description")

    if description is not None:
        description = str(description).strip()

        if len(description) > 5000:
            return error_response(
                "Description cannot exceed 5000 characters.",
                400,
            )

    # Prevent accidental duplicate plan names inside the same ISP.
    duplicate_statement = select(ServicePlan).where(
        ServicePlan.organization_id == organization_id,
        ServicePlan.name == name,
    )

    existing_plan = db.session.scalar(
        duplicate_statement
    )

    if existing_plan:
        return error_response(
            "A service plan with this name already exists.",
            409,
        )

    plan = ServicePlan(
        organization_id=organization_id,
        name=name,
        service_type=service_type,
        price=price,
        billing_period=billing_period,
        download_speed=download_speed,
        upload_speed=upload_speed,
        data_limit=data_limit,
        validity_days=validity_days,
        description=description,
        status=status,
    )

    db.session.add(plan)
    db.session.commit()

    return success_response(
        plan.to_dict(),
        "Service plan created successfully.",
        201,
    )


@service_plans_bp.get("/<int:plan_id>")
@jwt_required()
def get_service_plan(plan_id):
    """
    Retrieve one service plan belonging to the authenticated organization.
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    statement = select(ServicePlan).where(
        ServicePlan.id == plan_id,
        ServicePlan.organization_id == organization_id,
    )

    plan = db.session.scalar(statement)

    if plan is None:
        return error_response(
            "Service plan not found.",
            404,
        )

    return success_response(plan.to_dict())


@service_plans_bp.patch("/<int:plan_id>")
@jwt_required()
def update_service_plan(plan_id):
    """
    Update a service plan belonging to the authenticated organization.
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    statement = select(ServicePlan).where(
        ServicePlan.id == plan_id,
        ServicePlan.organization_id == organization_id,
    )

    plan = db.session.scalar(statement)

    if plan is None:
        return error_response(
            "Service plan not found.",
            404,
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "Request body must be a JSON object.",
            400,
        )

    if "name" in data:
        name = str(data["name"]).strip()

        if not name:
            return error_response(
                "Plan name cannot be empty.",
                400,
            )

        if len(name) > 150:
            return error_response(
                "Plan name cannot exceed 150 characters.",
                400,
            )

        duplicate_statement = select(ServicePlan).where(
            ServicePlan.organization_id == organization_id,
            ServicePlan.name == name,
            ServicePlan.id != plan.id,
        )

        existing_plan = db.session.scalar(
            duplicate_statement
        )

        if existing_plan:
            return error_response(
                "A service plan with this name already exists.",
                409,
            )

        plan.name = name

    if "service_type" in data:
        service_type = str(
            data["service_type"]
        ).strip().lower()

        if service_type not in ALLOWED_SERVICE_TYPES:
            return error_response(
                "service_type must be one of: pppoe, hotspot, static.",
                400,
            )

        plan.service_type = service_type

    if "price" in data:
        price = validate_price(data["price"])

        if price is None:
            return error_response(
                "Price must be a valid non-negative number.",
                400,
            )

        plan.price = price

    if "billing_period" in data:
        billing_period = str(
            data["billing_period"]
        ).strip().lower()

        if billing_period not in ALLOWED_BILLING_PERIODS:
            return error_response(
                "billing_period must be one of: daily, weekly, monthly, quarterly, yearly.",
                400,
            )

        plan.billing_period = billing_period

    if "download_speed" in data:
        download_speed, error = validate_positive_integer(
            data["download_speed"],
            "download_speed",
        )

        if error:
            return error_response(error, 400)

        plan.download_speed = download_speed

    if "upload_speed" in data:
        upload_speed, error = validate_positive_integer(
            data["upload_speed"],
            "upload_speed",
        )

        if error:
            return error_response(error, 400)

        plan.upload_speed = upload_speed

    if "data_limit" in data:
        data_limit, error = validate_positive_integer(
            data["data_limit"],
            "data_limit",
        )

        if error:
            return error_response(error, 400)

        plan.data_limit = data_limit

    if "validity_days" in data:
        validity_days, error = validate_positive_integer(
            data["validity_days"],
            "validity_days",
        )

        if error:
            return error_response(error, 400)

        plan.validity_days = validity_days

    if "description" in data:
        description = data["description"]

        if description is None:
            plan.description = None
        else:
            description = str(description).strip()

            if len(description) > 5000:
                return error_response(
                    "Description cannot exceed 5000 characters.",
                    400,
                )

            plan.description = description

    if "status" in data:
        status = str(
            data["status"]
        ).strip().lower()

        if status not in ALLOWED_STATUSES:
            return error_response(
                "status must be active or inactive.",
                400,
            )

        plan.status = status

    db.session.commit()

    return success_response(
        plan.to_dict(),
        "Service plan updated successfully.",
    )


@service_plans_bp.patch("/<int:plan_id>/status")
@jwt_required()
def update_service_plan_status(plan_id):
    """
    Change only the status of a service plan.
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    statement = select(ServicePlan).where(
        ServicePlan.id == plan_id,
        ServicePlan.organization_id == organization_id,
    )

    plan = db.session.scalar(statement)

    if plan is None:
        return error_response(
            "Service plan not found.",
            404,
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "Request body must be a JSON object.",
            400,
        )

    status = str(
        data.get("status", "")
    ).strip().lower()

    if status not in ALLOWED_STATUSES:
        return error_response(
            "status must be active or inactive.",
            400,
        )

    plan.status = status

    db.session.commit()

    return success_response(
        plan.to_dict(),
        "Service plan status updated successfully.",
    )


@service_plans_bp.delete("/<int:plan_id>")
@jwt_required()
def delete_service_plan(plan_id):
    """
    Delete a service plan belonging to the authenticated organization.

    Deletion will later need additional protection once customer
    service subscriptions reference plans.
    """
    user = get_current_user()

    if user is None or not user.is_active:
        return error_response(
            "Authenticated user not found or inactive.",
            401,
        )

    organization_id = get_organization_id(user)

    if organization_id is None:
        return error_response(
            "An organization context is required.",
            403,
        )

    statement = select(ServicePlan).where(
        ServicePlan.id == plan_id,
        ServicePlan.organization_id == organization_id,
    )

    plan = db.session.scalar(statement)

    if plan is None:
        return error_response(
            "Service plan not found.",
            404,
        )

    db.session.delete(plan)
    db.session.commit()

    return success_response(
        message="Service plan deleted successfully.",
    )