from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class ServicePlan(db.Model):
    __tablename__ = "service_plans"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    service_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    billing_period: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    download_speed: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    upload_speed: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    data_limit: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    validity_days: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
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
            "organization_id": self.organization_id,
            "name": self.name,
            "service_type": self.service_type,
            "price": float(self.price),
            "billing_period": self.billing_period,
            "download_speed": self.download_speed,
            "upload_speed": self.upload_speed,
            "data_limit": self.data_limit,
            "validity_days": self.validity_days,
            "description": self.description,
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