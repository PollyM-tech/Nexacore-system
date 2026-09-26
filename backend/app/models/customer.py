from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def generate_customer_code():
    return f"CUS-{uuid4().hex[:8].upper()}"


class Customer(db.Model):
    __tablename__ = "customers"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "phone",
            name="uq_customer_organization_phone",
        ),
        UniqueConstraint(
            "organization_id",
            "email",
            name="uq_customer_organization_email",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    customer_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        default=generate_customer_code,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "customer_code": self.customer_code,
            "organization_id": self.organization_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "notes": self.notes,
            "status": self.status,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }