from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from factors.shared.adapters.orm_base import Base


class CombinationRow(Base):
    __tablename__ = "combinations"
    __table_args__ = (
        UniqueConstraint(
            "decision_table_id", "signature", name="uq_combination_signature"
        ),
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
        UniqueConstraint(
            "combination_id", "factor_id", name="uq_combination_value_factor"
        ),
        Index("ix_combination_values_factor_value", "factor_id", "factor_value_id"),
        Index("ix_combination_values_combination", "combination_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("combinations.id", ondelete="CASCADE"), nullable=False
    )
    factor_id: Mapped[int] = mapped_column(
        ForeignKey("factors.id", ondelete="CASCADE"), nullable=False
    )
    factor_value_id: Mapped[int] = mapped_column(
        ForeignKey("factor_values.id", ondelete="CASCADE"), nullable=False
    )

    combination: Mapped[CombinationRow] = relationship(back_populates="values")
