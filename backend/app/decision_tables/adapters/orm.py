"""SQLAlchemy table mappings for the `decision_tables` context. See
`specs/features/decision_tables/*.md` and the plan's "Storage schema"
section for the rationale behind each column/index/constraint."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.orm_base import Base


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
    __table_args__ = (UniqueConstraint("decision_table_id", "name", name="uq_factor_table_name"),)

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
    factor_id: Mapped[int] = mapped_column(ForeignKey("factors.id", ondelete="CASCADE"), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    factor: Mapped[FactorRow] = relationship(back_populates="values")


class GenerationJobRow(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (Index("ix_generation_jobs_table_status", "decision_table_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_table_id: Mapped[int] = mapped_column(
        ForeignKey("decision_tables.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    total_combinations: Mapped[int] = mapped_column(Integer, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CombinationRow(Base):
    __tablename__ = "combinations"
    __table_args__ = (
        UniqueConstraint("decision_table_id", "signature", name="uq_combination_signature"),
        Index("ix_combinations_table_status", "decision_table_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_table_id: Mapped[int] = mapped_column(
        ForeignKey("decision_tables.id", ondelete="CASCADE"), nullable=False
    )
    generation_job_id: Mapped[int] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="unreviewed")
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    impossible_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    values: Mapped[list[CombinationValueRow]] = relationship(
        back_populates="combination", cascade="all, delete-orphan"
    )


class CombinationValueRow(Base):
    __tablename__ = "combination_values"
    __table_args__ = (
        UniqueConstraint("combination_id", "factor_id", name="uq_combination_value_factor"),
        Index("ix_combination_values_factor_value", "factor_id", "factor_value_id"),
        Index("ix_combination_values_combination", "combination_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("combinations.id", ondelete="CASCADE"), nullable=False
    )
    factor_id: Mapped[int] = mapped_column(ForeignKey("factors.id", ondelete="CASCADE"), nullable=False)
    factor_value_id: Mapped[int] = mapped_column(
        ForeignKey("factor_values.id", ondelete="CASCADE"), nullable=False
    )

    combination: Mapped[CombinationRow] = relationship(back_populates="values")


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
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    factor_id: Mapped[int] = mapped_column(ForeignKey("factors.id", ondelete="CASCADE"), nullable=False)
    factor_value_id: Mapped[int] = mapped_column(
        ForeignKey("factor_values.id", ondelete="CASCADE"), nullable=False
    )

    rule: Mapped[RuleRow] = relationship(back_populates="values")
