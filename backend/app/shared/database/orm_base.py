from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Table mappings themselves live in each
    bounded context's `adapters/orm.py` — this base is the only thing that
    needs to be cross-context (Alembic autogenerate needs one `Base.metadata`
    to diff against)."""
