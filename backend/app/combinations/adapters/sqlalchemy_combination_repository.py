from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.combinations.adapters.combination_filters import apply_combination_filter
from app.combinations.adapters.orm import CombinationRow, CombinationValueRow
from app.combinations.entities import Combination, CombinationValue
from app.combinations.ports.combination_repository import (
    CombinationFilter,
    CombinationPatch,
    CombinationRepository,
)


def row_to_combination(row: CombinationRow) -> Combination:
    return Combination(
        id=row.id,
        decision_table_id=row.decision_table_id,
        generation_job_id=row.generation_job_id,
        signature=row.signature,
        status=row.status,  # type: ignore[arg-type]
        output=row.output,
        impossible_reason=row.impossible_reason,
        values=[
            CombinationValue(factor_id=v.factor_id, factor_value_id=v.factor_value_id)
            for v in row.values
        ],
    )


class SqlAlchemyCombinationRepository(CombinationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, combinations: list[Combination]) -> None:
        """Insert a batch of newly-generated combinations in one set-based
        operation."""
        if not combinations:
            return
        rows = [
            CombinationRow(
                decision_table_id=c.decision_table_id,
                generation_job_id=c.generation_job_id,
                status=str(c.status),
                output=c.output,
                impossible_reason=c.impossible_reason,
                signature=c.signature,
            )
            for c in combinations
        ]
        self._session.add_all(rows)
        await self._session.flush()

        value_rows = [
            CombinationValueRow(
                combination_id=row.id,
                factor_id=value.factor_id,
                factor_value_id=value.factor_value_id,
            )
            for row, combination in zip(rows, combinations, strict=True)
            for value in combination.values
        ]
        self._session.add_all(value_rows)
        await self._session.flush()

    async def get(self, table_id: int, combination_id: int) -> Combination | None:
        """Return one combination, or None if it doesn't exist on this table."""
        stmt = (
            select(CombinationRow)
            .where(
                CombinationRow.id == combination_id,
                CombinationRow.decision_table_id == table_id,
            )
            .options(selectinload(CombinationRow.values))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return None if row is None else row_to_combination(row)

    async def save(self, combination: Combination) -> None:
        """Persist status/output/impossible_reason for one already-existing
        combination."""
        assert combination.id is not None
        row = await self._session.get(CombinationRow, combination.id)
        assert row is not None
        row.status = str(combination.status)
        row.output = combination.output
        row.impossible_reason = combination.impossible_reason
        await self._session.flush()

    async def bulk_update_status(
        self, table_id: int, filter_: CombinationFilter, patch: CombinationPatch
    ) -> tuple[int, int]:
        """Apply `patch` to every combination in `table_id` matching
        `filter_` in one set-based UPDATE. Returns (matched_count,
        updated_count) — the two are equal in v1 since there's no
        concurrent-modification detection, but kept distinct in the
        signature for that future case."""
        matched_stmt = apply_combination_filter(
            select(CombinationRow.id), table_id, filter_
        )
        matched_ids = [
            row[0] for row in (await self._session.execute(matched_stmt)).all()
        ]
        if not matched_ids:
            return 0, 0

        values: dict[str, object] = {}
        if patch.status is not None:
            values["status"] = str(patch.status)
        if patch.output_set:
            values["output"] = patch.output
        if patch.impossible_reason_set:
            values["impossible_reason"] = patch.impossible_reason

        if not values:
            return len(matched_ids), 0

        stmt = (
            update(CombinationRow)
            .where(CombinationRow.id.in_(matched_ids))
            .values(**values)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return len(matched_ids), result.rowcount or 0

    async def delete_all_for_table(self, table_id: int) -> None:
        """Used both by regeneration (delete-and-recreate) and by factor/
        value deletion (invalidates existing combinations' signatures)."""
        stmt = delete(CombinationRow).where(
            CombinationRow.decision_table_id == table_id
        )
        await self._session.execute(stmt)
        await self._session.flush()
