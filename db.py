import os
import pandas as pd
from sqlalchemy import create_engine


def get_engine():

    conn = (
        f"mysql+pymysql://"
        f"{os.environ['DB_USER']}:"
        f"{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:3306/"
        f"{os.environ['DB_DATABASE']}"
    )

    return create_engine(conn)


def load_latest_maintenance():

    query = """
    SELECT
        tm.trolleyId,
        tt.trolleyName,
        tt.serialNo,
        tm.type,
        tm.reason,
        tm.createdOn
    FROM tbl_trolley_maintenance_synthetic tm
    INNER JOIN tbl_trolley tt
        ON tm.trolleyId = tt.trolleyId
    """

    return pd.read_sql(query, get_engine())

def save_predictions(df):

    df.to_sql(
        "tbl_predictive_maintainanence",
        con=get_engine(),
        if_exists="append",
        index=False
    )
    
    
def get_latest_forecast_date():

    query = """
    SELECT MAX(nextmaintenancedate) AS latest_date
    FROM tbl_predictive_maintainanence
    """

    df = pd.read_sql(query, get_engine())

    return df.iloc[0]["latest_date"]

def get_prediction_window():

    latest_date = get_latest_forecast_date()

    today = pd.Timestamp.now().normalize()

    # table empty
    if latest_date is None or pd.isna(latest_date):

        start_date = today
        end_date = today + pd.Timedelta(days=9)

    # table already contains forecasts
    else:

        start_date = (
            pd.to_datetime(latest_date)
            + pd.Timedelta(days=1)
        )

        end_date = start_date

    return start_date.normalize(), end_date.normalize()