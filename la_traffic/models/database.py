from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from la_traffic.config import settings


def get_engine() -> Engine:
    """Create and return a SQLAlchemy engine."""
    return create_engine(settings.database_url)
