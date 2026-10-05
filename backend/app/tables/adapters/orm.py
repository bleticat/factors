from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.adapters.orm_base import Base


class DecisionTableRow(Base):
    __tablename__ = "decision_tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    factors: Mapped[list[FactorRow]] = relationship(
        back_populates="decision_table",
        cascade="all, delete-orphan",
        order_by="FactorRow.order_index",
    )


class FactorRow(Base):
    __tablename__ = "factors"
    __table_args__ = (
        UniqueConstraint("decision_table_id", "name", name="uq_factor_table_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_table_id: Mapped[int] = mapped_column(
        ForeignKey("decision_tables.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    decision_table: Mapped[DecisionTableRow] = relationship(back_populates="factors")
    values: Mapped[list[FactorValueRow]] = relationship(
        back_populates="factor",
        cascade="all, delete-orphan",
        order_by="FactorValueRow.order_index",
    )


class FactorValueRow(Base):
    __tablename__ = "factor_values"
    __table_args__ = (UniqueConstraint("factor_id", "value", name="uq_factor_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    factor_id: Mapped[int] = mapped_column(
        ForeignKey("factors.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    factor: Mapped[FactorRow] = relationship(back_populates="values")
