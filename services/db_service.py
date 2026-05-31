import pandas as pd

from sqlalchemy import create_engine

from config.settings import *

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"
)


def insert_predictions(df):

    df.to_sql(
        "tbl_predicted_maintenance",
        con=engine,
        if_exists="append",
        index=False
    )


def get_latest_maintenance_data():

    query = """
    SELECT
        trolleyId,
        type,
        reason,
        MAX(createdOn) as createdOn
    FROM tbl_trolley_maintenance_50k
    GROUP BY trolleyId,type,reason
    """

    return pd.read_sql(query, engine)