import os
import pandas as pd
from sqlalchemy import create_engine


def get_engine():

    conn = (
        f"mysql+pymysql://"
        f"{os.environ['DB_USER']}:"
        f"{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:3306/"
        f"{os.environ['DB_NAME']}"
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
    FROM tbl_trolley_maintenance_synthetic_2_0 tm
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
    
    
