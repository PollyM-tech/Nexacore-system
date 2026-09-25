from flask import Blueprint, request

from sqlalchemy import select

from app.authz import super_admin_required
from app.extensions import db
from app.models.organization import Organization
from app.models.admin_user import AdminUser


organizations_bp = Blueprint(
    "organizations",
    __name__,
    url_prefix="/api/v1/organizations",
)


# ============================================================
# CREATE ORGANIZATION
# POST /api/v1/organizations
# ============================================================

@organizations_bp.post("")
@super_admin_required()
def create_organization():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    slug = str(
        data.get("slug", "")
    ).strip().lower()

    phone = str(
        data.get("phone", "")
    ).strip() or None

    email = str(
        data.get("email", "")
    ).strip().lower() or None

    address = str(
        data.get("address", "")
    ).strip() or None

    county = str(
        data.get("county", "")
    ).strip() or None

    notes = str(
        data.get("notes", "")
    ).strip() or None


    if not name or not slug:
        return {
            "status": "error",
            "message": "Organization name and slug are required.",
        }, 400


    existing_slug = db.session.scalar(
        select(Organization).where(
            Organization.slug == slug
        )
    )


    if existing_slug:
        return {
            "status": "error",
            "message": "Organization slug already exists.",
        }, 409


    organization = Organization(
        name=name,
        slug=slug,
        phone=phone,
        email=email,
        address=address,
        county=county,
        country="Kenya",
        status="active",
        is_active=True,
        notes=notes,
    )


    db.session.add(organization)
    db.session.commit()


    return {
        "status": "success",
        "message": "Organization created successfully.",
        "data": {
            "organization": organization.to_dict()
        },
    }, 201



# ============================================================
# LIST ORGANIZATIONS
# GET /api/v1/organizations
# ============================================================

@organizations_bp.get("")
@super_admin_required()
def list_organizations():

    organizations = db.session.scalars(
        select(Organization).order_by(
            Organization.created_at.desc()
        )
    ).all()


    return {
        "status": "success",
        "data": {
            "organizations": [
                organization.to_dict()
                for organization in organizations
            ]
        },
    }, 200



# ============================================================
# GET SINGLE ORGANIZATION
# GET /api/v1/organizations/<id>
# ============================================================

@organizations_bp.get("/<int:organization_id>")
@super_admin_required()
def get_organization(organization_id):

    organization = db.session.get(
        Organization,
        organization_id,
    )


    if organization is None:
        return {
            "status": "error",
            "message": "Organization not found.",
        }, 404


    return {
        "status": "success",
        "data": {
            "organization": organization.to_dict()
        },
    }, 200



# ============================================================
# CREATE ORGANIZATION USER
# POST /api/v1/organizations/<id>/users
# ============================================================

@organizations_bp.post("/<int:organization_id>/users")
@super_admin_required()
def create_organization_user(organization_id):

    data = request.get_json(silent=True) or {}


    full_name = str(
        data.get("full_name", "")
    ).strip()


    email = str(
        data.get("email", "")
    ).strip().lower()


    password = str(
        data.get("password", "")
    )


    role = str(
        data.get(
            "role",
            "organization_admin"
        )
    ).strip()



    if not full_name or not email or not password:
        return {
            "status": "error",
            "message": "Full name, email and password are required.",
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



    existing_user = db.session.scalar(
        select(AdminUser).where(
            AdminUser.email == email
        )
    )


    if existing_user:
        return {
            "status": "error",
            "message": "Email already exists.",
        }, 409



    user = AdminUser(
        full_name=full_name,
        email=email,
        role=role,
        organization_id=organization.id,
        is_active=True,
    )


    user.set_password(password)


    db.session.add(user)
    db.session.commit()



    return {
        "status": "success",
        "message": "Organization user created successfully.",
        "data": {
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "organization": {
                    "id": organization.id,
                    "name": organization.name,
                    "slug": organization.slug,
                },
            }
        },
    }, 201