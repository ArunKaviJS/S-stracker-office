import pandas as pd
from sqlalchemy import create_engine, text
import os


engine = create_engine(
    f"mysql+pymysql://{os.environ['DB_USER']}:"
    f"{os.environ['DB_PASSWORD']}@"
    f"{os.environ['DB_HOST']}:3306/"
    f"{os.environ['DB_NAME']}"
)


def get_geozones():

    query = """
    SELECT DISTINCT
        dh.geozoneId,
        dh.geolayerId,
        gz.geozoneName
    FROM tbl_device_history dh
    INNER JOIN tbl_geozones gz
        ON dh.geozoneId = gz.geozoneId
    WHERE dh.geozoneId <> 0
    """

    return pd.read_sql(query, engine)

def truncate_forecast_table():

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE tbl_trolley_forecast"))

def save_forecasts(df):

    df.to_sql(
        "tbl_trolley_forecast",
        engine,
        if_exists="append",
        index=False
    )