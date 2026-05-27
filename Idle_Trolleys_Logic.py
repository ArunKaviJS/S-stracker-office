import pandas as pd
import numpy as np

from sqlalchemy import text

# ============================================================
# IDLE TROLLEYS LOGIC
# ============================================================

def process_idle_trolleys(
    dest_engine
):

    # ========================================================
    # LOAD DATA
    # ========================================================

    df = pd.read_sql(
        "SELECT * FROM tbl_device_history_copy",
        dest_engine
    )

    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    df1 = df[[
        "trolleyId",
        "geozoneId",
        "createdOn",
        "status"
    ]].copy()

    # ========================================================
    # DATETIME
    # ========================================================

    df1["createdOn"] = pd.to_datetime(
        df1["createdOn"],
        errors="coerce"
    )

    # ========================================================
    # REMOVE NULLS
    # ========================================================

    df1 = df1.dropna(
        subset=[
            "trolleyId",
            "geozoneId",
            "createdOn"
        ]
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    df1 = df1.drop_duplicates(
        subset=[
            "trolleyId",
            "geozoneId",
            "createdOn"
        ]
    )

    # ========================================================
    # SORT
    # ========================================================

    df1 = df1.sort_values(
        by=[
            "trolleyId",
            "createdOn"
        ]
    ).reset_index(drop=True)

    # ========================================================
    # PREVIOUS GEOZONE
    # ========================================================

    df1["prev_geozone"] = (
        df1.groupby("trolleyId")["geozoneId"]
        .shift(1)
    )

    df1["zone_changed"] = (
        df1["geozoneId"] != df1["prev_geozone"]
    )

    # ========================================================
    # STREAK ID
    # ========================================================

    df1["streak_id"] = (
        df1.groupby("trolleyId")["zone_changed"]
        .cumsum()
    )

    # ========================================================
    # STREAKS
    # ========================================================

    streaks = (
        df1.groupby(
            [
                "trolleyId",
                "geozoneId",
                "streak_id"
            ]
        )
        .agg(
            start_time=("createdOn", "min"),
            end_time=("createdOn", "max"),
            records=("createdOn", "count")
        )
        .reset_index()
    )

    # ========================================================
    # IDLE HOURS
    # ========================================================

    streaks["idle_hours"] = (
        (
            streaks["end_time"] -
            streaks["start_time"]
        )
        .dt.total_seconds() / 3600
    )

    # ========================================================
    # STATUS
    # ========================================================

    conditions = [
        streaks["idle_hours"] >= 24,
        streaks["idle_hours"] >= 6,
        streaks["idle_hours"] >= 2
    ]

    choices = [
        "Critical",
        "Severe",
        "Idle"
    ]

    streaks["idle_status"] = np.select(
        conditions,
        choices,
        default="Normal"
    )

    # ========================================================
    # FILTER
    # ========================================================

    idle_trolleys = streaks[
        streaks["idle_status"].isin(
            [
                "Idle",
                "Severe",
                "Critical"
            ]
        )
    ]

    # ========================================================
    # FINAL COLUMNS
    # ========================================================

    idle_trolleys = idle_trolleys[
        [
            "trolleyId",
            "geozoneId",
            "idle_hours",
            "idle_status"
        ]
    ]

    # ========================================================
    # SORT
    # ========================================================

    idle_trolleys = idle_trolleys.sort_values(
        by="idle_hours",
        ascending=False
    )

    # ========================================================
    # CREATE TABLE
    # ========================================================

    create_table_query = """
    CREATE TABLE IF NOT EXISTS tbl_idle_trolleys (
        trolleyId BIGINT,
        geozoneId BIGINT,
        idle_hours FLOAT,
        idle_status VARCHAR(50)
    )
    """

    with dest_engine.begin() as conn:
        conn.execute(text(create_table_query))

    # ========================================================
    # CLEAR OLD DATA
    # ========================================================

    with dest_engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE tbl_idle_trolleys")
        )

    # ========================================================
    # STORE DATA
    # ========================================================

    idle_trolleys.to_sql(
        "tbl_idle_trolleys",
        dest_engine,
        if_exists="append",
        index=False
    )

    print("Idle Trolleys Stored")