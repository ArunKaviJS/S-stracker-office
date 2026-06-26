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
        gz.geozoneName
    FROM tbl_device_history dh
    INNER JOIN tbl_geozones gz
        ON dh.geozoneId = gz.geozoneId
    WHERE dh.geozoneId <> 0
    """

    return pd.read_sql(query, engine)



def save_forecasts(df):

    df.to_sql(
        "tbl_trolley_forecast",
        engine,
        if_exists="append",
        index=False
    )
    
    
def get_latest_forecast_date():

    query = """
    SELECT MAX(forecast_date) AS max_date
    FROM tbl_trolley_forecast
    """

    result = pd.read_sql(query, engine)

    return result.iloc[0]["max_date"]


