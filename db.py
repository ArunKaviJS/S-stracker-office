import pandas as pd
from sqlalchemy import create_engine
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
        geozoneId,
        geolayerId
    FROM tbl_device_history
    WHERE geozoneId <> 0
    """

    return pd.read_sql(query, engine)


def save_forecasts(df):

    df.to_sql(
        "tbl_trolley_demand_forecast",
        engine,
        if_exists="append",
        index=False
    )