import pytest


async def test_transaction_data_access_rejects_use_after_block_exits(database):
    async with database.transaction() as db:
        leaked = db

    with pytest.raises(RuntimeError, match="tables"):
        await leaked.tables.get(1)


async def test_snapshot_data_access_rejects_use_after_block_exits(database):
    async with database.snapshot() as db:
        leaked = db

    with pytest.raises(RuntimeError, match="tables_reader"):
        await leaked.tables_reader.get(1)


async def test_transaction_data_access_rejects_use_after_exception(database):
    leaked = None
    with pytest.raises(ValueError):
        async with database.transaction() as db:
            leaked = db
            raise ValueError("boom")

    with pytest.raises(RuntimeError, match="rules"):
        await leaked.rules.list_for_table(1)


async def test_data_access_works_normally_within_its_own_block(database):
    async with database.transaction() as db:
        table = await db.tables.get(1)
        assert table is None
