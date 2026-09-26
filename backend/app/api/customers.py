from flask import Blueprint, request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.authz import (
    admin_required,
    get_current_user,
)
from app.extensions import db
from app.models.customer import Customer
from app.models.organization import Organization


customers_bp = Blueprint(
    "customers",
    __name__,
    url_prefix="/api/v1/customers",
)


# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(phone: str) -> str:
    """
    Normalize Kenyan phone numbers into the 254XXXXXXXXX format.

    Examples:

        0712345678
        +254712345678
        254712345678

    become:

        254712345678
    """

    phone = phone.strip().replace(" ", "")

    if phone.startswith("+254"):
        return phone[1:]

    if phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]

    return phone


# ============================================================
# CUSTOMER ACCESS SCOPE
# ============================================================

def customer_scope_statement(user):
    """
    Return a Customer query scoped to the authenticated user.

    Super admins:
        Can access customers across all organizations.

    Organization admins:
        Can only access customers belonging to their
        own organization.
    """

    statement = select(Customer)

    if user.role == "organization_admin":

        if user.organization_id is None:
            # This should normally never happen because an
            # organization admin must belong to an organization.
            statement = statement.where(
                Customer.id == -1
            )

        else:
            statement = statement.where(
                Customer.organization_id == user.organization_id
            )

    return statement


# ============================================================
# LIST CUSTOMERS
# ============================================================

@customers_bp.get("")
@admin_required()
def list_customers():

    user = get_current_user()

    if user is None:
        return {
            "status": "error",
            "message": "Authenticated user not found.",
        }, 401

    page = request.args.get(
        "page",
        default=1,
        type=int,
    )

    per_page = request.args.get(
        "per_page",
        default=20,
        type=int,
    )

    search = request.args.get(
        "search",
        default="",
        type=str,
    ).strip()

    status = request.args.get(
        "status",
        default="",
        type=str,
    ).strip().lower()

    # Prevent unreasonable pagination values.
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)

    statement = customer_scope_statement(user)

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        pattern = f"%{search}%"

        statement = statement.where(
            or_(
                Customer.full_name.ilike(pattern),
                Customer.phone.ilike(pattern),
                Customer.customer_code.ilike(pattern),
                Customer.email.ilike(pattern),
            )
        )

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    if status:

        allowed_statuses = {
            "active",
            "suspended",
            "inactive",
        }

        if status not in allowed_statuses:
            return {
                "status": "error",
                "message": "Invalid customer status.",
            }, 400

        statement = statement.where(
            Customer.status == status
        )

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    statement = statement.order_by(
        Customer.created_at.desc()
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    pagination = db.paginate(
        statement,
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return {
        "status": "success",
        "data": {
            "customers": [
                customer.to_dict()
                for customer in pagination.items
            ],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        },
    }, 200


# ============================================================
# CREATE CUSTOMER
# ============================================================

@customers_bp.post("")
@admin_required()
def create_customer():

    user = get_current_user()

    if user is None:
        return {
            "status": "error",
            "message": "Authenticated user not found.",
        }, 401

    data = request.get_json(silent=True) or {}

    # --------------------------------------------------------
    # BASIC FIELDS
    # --------------------------------------------------------

    full_name = str(
        data.get("full_name", "")
    ).strip()

    phone = normalize_phone(
        str(data.get("phone", ""))
    )

    email = str(
        data.get("email", "")
    ).strip().lower() or None

    address = str(
        data.get("address", "")
    ).strip() or None

    notes = str(
        data.get("notes", "")
    ).strip() or None

    # --------------------------------------------------------
    # REQUIRED FIELDS
    # --------------------------------------------------------

    if not full_name:
        return {
            "status": "error",
            "message": "Full name is required.",
        }, 400

    if not phone:
        return {
            "status": "error",
            "message": "Phone number is required.",
        }, 400

    # --------------------------------------------------------
    # DETERMINE ORGANIZATION
    # --------------------------------------------------------

    organization_id = None

    # Organization administrator
    if user.role == "organization_admin":

        if user.organization_id is None:
            return {
                "status": "error",
                "message": "User is not assigned to an organization.",
            }, 403

        # IMPORTANT:
        # Never trust organization_id supplied by the frontend.
        organization_id = user.organization_id

    # Super administrator
    elif user.role == "super_admin":

        organization_id = data.get(
            "organization_id"
        )

        if organization_id is None:
            return {
                "status": "error",
                "message": (
                    "organization_id is required "
                    "for super administrators."
                ),
            }, 400

        try:
            organization_id = int(
                organization_id
            )

        except (TypeError, ValueError):

            return {
                "status": "error",
                "message": (
                    "organization_id must be "
                    "a valid integer."
                ),
            }, 400

        organization = db.session.get(
            Organization,
            organization_id,
        )

        if organization is None:
            return {
                "status": "error",
                "message": "Organization not found.",
            }, 404

        if not organization.is_active:
            return {
                "status": "error",
                "message": "Organization is inactive.",
            }, 403

    else:

        return {
            "status": "error",
            "message": "Unauthorized access.",
        }, 403

    # --------------------------------------------------------
    # CHECK PHONE WITHIN ORGANIZATION
    # --------------------------------------------------------

    existing_phone = db.session.scalar(
        select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.phone == phone,
        )
    )

    if existing_phone is not None:

        return {
            "status": "error",
            "message": (
                "A customer with this phone number "
                "already exists in this organization."
            ),
        }, 409

    # --------------------------------------------------------
    # CHECK EMAIL WITHIN ORGANIZATION
    # --------------------------------------------------------

    if email:

        existing_email = db.session.scalar(
            select(Customer).where(
                Customer.organization_id == organization_id,
                Customer.email == email,
            )
        )

        if existing_email is not None:

            return {
                "status": "error",
                "message": (
                    "A customer with this email "
                    "already exists in this organization."
                ),
            }, 409

    # --------------------------------------------------------
    # CREATE CUSTOMER
    # --------------------------------------------------------

    customer = Customer(
        organization_id=organization_id,
        full_name=full_name,
        phone=phone,
        email=email,
        address=address,
        notes=notes,
        status="active",
    )

    try:

        db.session.add(customer)
        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        return {
            "status": "error",
            "message": (
                "Unable to create customer because "
                "the phone number or email is already "
                "in use within this organization."
            ),
        }, 409

    return {
        "status": "success",
        "message": "Customer created successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 201


# ============================================================
# GET SINGLE CUSTOMER
# ============================================================

@customers_bp.get("/<int:customer_id>")
@admin_required()
def get_customer(customer_id):

    user = get_current_user()

    if user is None:
        return {
            "status": "error",
            "message": "Authenticated user not found.",
        }, 401

    statement = customer_scope_statement(
        user
    ).where(
        Customer.id == customer_id
    )

    customer = db.session.scalar(
        statement
    )

    if customer is None:

        return {
            "status": "error",
            "message": "Customer not found.",
        }, 404

    return {
        "status": "success",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 200


# ============================================================
# UPDATE CUSTOMER
# ============================================================

@customers_bp.patch("/<int:customer_id>")
@admin_required()
def update_customer(customer_id):

    user = get_current_user()

    if user is None:
        return {
            "status": "error",
            "message": "Authenticated user not found.",
        }, 401

    # --------------------------------------------------------
    # FIND CUSTOMER USING TENANT SCOPE
    # --------------------------------------------------------

    statement = customer_scope_statement(
        user
    ).where(
        Customer.id == customer_id
    )

    customer = db.session.scalar(
        statement
    )

    if customer is None:

        return {
            "status": "error",
            "message": "Customer not found.",
        }, 404

    data = request.get_json(
        silent=True
    ) or {}

    # --------------------------------------------------------
    # FULL NAME
    # --------------------------------------------------------

    if "full_name" in data:

        full_name = str(
            data["full_name"]
        ).strip()

        if not full_name:

            return {
                "status": "error",
                "message": "Full name cannot be empty.",
            }, 400

        customer.full_name = full_name

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    if "phone" in data:

        phone = normalize_phone(
            str(data["phone"])
        )

        if not phone:

            return {
                "status": "error",
                "message": "Phone number cannot be empty.",
            }, 400

        existing_phone = db.session.scalar(
            select(Customer).where(
                Customer.organization_id
                == customer.organization_id,

                Customer.phone == phone,

                Customer.id != customer.id,
            )
        )

        if existing_phone is not None:

            return {
                "status": "error",
                "message": (
                    "Phone number is already in use "
                    "within this organization."
                ),
            }, 409

        customer.phone = phone

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    if "email" in data:

        email = str(
            data["email"] or ""
        ).strip().lower() or None

        if email:

            existing_email = db.session.scalar(
                select(Customer).where(
                    Customer.organization_id
                    == customer.organization_id,

                    Customer.email == email,

                    Customer.id != customer.id,
                )
            )

            if existing_email is not None:

                return {
                    "status": "error",
                    "message": (
                        "Email is already in use "
                        "within this organization."
                    ),
                }, 409

        customer.email = email

    # --------------------------------------------------------
    # ADDRESS
    # --------------------------------------------------------

    if "address" in data:

        customer.address = str(
            data["address"] or ""
        ).strip() or None

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    if "notes" in data:

        customer.notes = str(
            data["notes"] or ""
        ).strip() or None

    # --------------------------------------------------------
    # ORGANIZATION ID
    # --------------------------------------------------------
    #
    # NEVER accept organization_id here.
    #
    # Customers cannot be moved between organizations
    # through this endpoint.
    #
    # --------------------------------------------------------

    try:

        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        return {
            "status": "error",
            "message": (
                "Unable to update customer because "
                "the phone number or email is already "
                "in use within this organization."
            ),
        }, 409

    return {
        "status": "success",
        "message": "Customer updated successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 200


# ============================================================
# UPDATE CUSTOMER STATUS
# ============================================================

@customers_bp.patch(
    "/<int:customer_id>/status"
)
@admin_required()
def update_customer_status(customer_id):

    user = get_current_user()

    if user is None:
        return {
            "status": "error",
            "message": "Authenticated user not found.",
        }, 401

    # --------------------------------------------------------
    # FIND CUSTOMER USING TENANT SCOPE
    # --------------------------------------------------------

    statement = customer_scope_statement(
        user
    ).where(
        Customer.id == customer_id
    )

    customer = db.session.scalar(
        statement
    )

    if customer is None:

        return {
            "status": "error",
            "message": "Customer not found.",
        }, 404

    data = request.get_json(
        silent=True
    ) or {}

    status = str(
        data.get("status", "")
    ).strip().lower()

    allowed_statuses = {
        "active",
        "suspended",
        "inactive",
    }

    if status not in allowed_statuses:

        return {
            "status": "error",
            "message": "Invalid customer status.",
        }, 400

    customer.status = status

    try:

        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        return {
            "status": "error",
            "message": "Unable to update customer status.",
        }, 409

    return {
        "status": "success",
        "message": "Customer status updated successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 200