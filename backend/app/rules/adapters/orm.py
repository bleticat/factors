"""SQLAlchemy table mappings owned by the `rules` module. FK columns
reference `tables`' tables by name only — no Python-level import of their
ORM rows is needed (see `app/tables/adapters/orm.py`)."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.adapters.orm_base import Base


class RuleRow(Base):
    __tablename__ = "rules"
    __table_args__ = (Index("ix_rules_table", "decision_table_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_table_id: Mapped[int] = mapped_column(
        ForeignKey("decision_tables.id", ondelete="CASCADE"), nullable=False
    )
    output: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    values: Mapped[list[RuleValueRow]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", order_by="RuleValueRow.id"
    )


class RuleValueRow(Base):
    __tablename__ = "rule_values"
    __table_args__ = (
        UniqueConstraint("rule_id", "factor_id", name="uq_rule_value_factor"),
        Index("ix_rule_values_rule", "rule_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )
    factor_id: Mapped[int] = mapped_column(
        ForeignKey("factors.id", ondelete="CASCADE"), nullable=False
    )
    factor_value_id: Mapped[int] = mapped_column(
        ForeignKey("factor_values.id", ondelete="CASCADE"), nullable=False
    )

    rule: Mapped[RuleRow] = relationship(back_populates="values")
