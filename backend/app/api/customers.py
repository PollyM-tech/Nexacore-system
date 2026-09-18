from flask import Blueprint, request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.authz import super_admin_required
from app.extensions import db
from app.models.customer import Customer


customers_bp = Blueprint(
    "customers",
    __name__,
    url_prefix="/api/v1/customers",
)


def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "")

    if phone.startswith("+254"):
        return phone[1:]

    if phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]

    return phone


@customers_bp.get("")
@super_admin_required()
def list_customers():
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

    per_page = min(max(per_page, 1), 100)

    statement = select(Customer)

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

    if status:
        statement = statement.where(
            Customer.status == status
        )

    statement = statement.order_by(
        Customer.created_at.desc()
    )

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


@customers_bp.post("")
@super_admin_required()
def create_customer():
    data = request.get_json(silent=True) or {}

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

    if not full_name or not phone:
        return {
            "status": "error",
            "message": "Full name and phone number are required.",
        }, 400

    existing_phone = db.session.scalar(
        select(Customer).where(
            Customer.phone == phone
        )
    )

    if existing_phone is not None:
        return {
            "status": "error",
            "message": "A customer with this phone number already exists.",
        }, 409

    if email:
        existing_email = db.session.scalar(
            select(Customer).where(
                Customer.email == email
            )
        )

        if existing_email is not None:
            return {
                "status": "error",
                "message": "A customer with this email already exists.",
            }, 409

    customer = Customer(
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
            "message": "Unable to create customer because of conflicting data.",
        }, 409

    return {
        "status": "success",
        "message": "Customer created successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 201


@customers_bp.get("/<int:customer_id>")
@super_admin_required()
def get_customer(customer_id):
    customer = db.session.get(
        Customer,
        customer_id,
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


@customers_bp.patch("/<int:customer_id>")
@super_admin_required()
def update_customer(customer_id):
    customer = db.session.get(
        Customer,
        customer_id,
    )

    if customer is None:
        return {
            "status": "error",
            "message": "Customer not found.",
        }, 404

    data = request.get_json(silent=True) or {}

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

    if "phone" in data:
        phone = normalize_phone(
            str(data["phone"])
        )

        existing_phone = db.session.scalar(
            select(Customer).where(
                Customer.phone == phone,
                Customer.id != customer.id,
            )
        )

        if existing_phone:
            return {
                "status": "error",
                "message": "Phone number is already in use.",
            }, 409

        customer.phone = phone

    if "email" in data:
        email = str(
            data["email"] or ""
        ).strip().lower() or None

        if email:
            existing_email = db.session.scalar(
                select(Customer).where(
                    Customer.email == email,
                    Customer.id != customer.id,
                )
            )

            if existing_email:
                return {
                    "status": "error",
                    "message": "Email is already in use.",
                }, 409

        customer.email = email

    if "address" in data:
        customer.address = str(
            data["address"] or ""
        ).strip() or None

    if "notes" in data:
        customer.notes = str(
            data["notes"] or ""
        ).strip() or None

    db.session.commit()

    return {
        "status": "success",
        "message": "Customer updated successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 200


@customers_bp.patch("/<int:customer_id>/status")
@super_admin_required()
def update_customer_status(customer_id):
    customer = db.session.get(
        Customer,
        customer_id,
    )

    if customer is None:
        return {
            "status": "error",
            "message": "Customer not found.",
        }, 404

    data = request.get_json(silent=True) or {}

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

    db.session.commit()

    return {
        "status": "success",
        "message": "Customer status updated successfully.",
        "data": {
            "customer": customer.to_dict(),
        },
    }, 200