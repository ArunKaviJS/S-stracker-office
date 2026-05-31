import pandas as pd

from sqlalchemy import create_engine
from sqlalchemy import text

from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME
)

_engine = None


def get_engine():
    global _engine

    if _engine is None:

        _engine = create_engine(
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
            f"@{DB_HOST}:3306/{DB_NAME}",
            pool_pre_ping=True,
            pool_recycle=3600
        )

    return _engine


def execute_query(sql):

    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)

    return df