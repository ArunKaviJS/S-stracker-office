import pandas as pd
import numpy as np

from sqlalchemy import text

# ============================================================
# UNDERPERFORMING GEOZONES
# ============================================================

def process_underperforming_geozones(
    engine
):

    # ========================================================
    # LOAD DATA
    # ========================================================

    df2 = pd.read_sql(
    """
    SELECT
        trolleyId,
        geozoneId,
        createdOn
    FROM tbl_device_history
    """,
    engine
)

    # ========================================================
    # SORT
    # ========================================================

    df2 = df2.sort_values(
        by=[
            "trolleyId",
            "createdOn"
        ]
    ).reset_index(drop=True)

    # ========================================================
    # PREVIOUS GEOZONE
    # ========================================================

    df2["prev_geozone"] = (
        df2.groupby("trolleyId")["geozoneId"]
        .shift(1)
    )

    df2["zone_changed"] = (
        df2["geozoneId"] != df2["prev_geozone"]
    )

    # ========================================================
    # MOVEMENT DATA
    # ========================================================

    movement_df = df2[
        df2["zone_changed"] == True
    ].copy()

    # ========================================================
    # DATETIME
    # ========================================================

    movement_df["createdOn"] = pd.to_datetime(
        movement_df["createdOn"],
        errors="coerce"
    )

    movement_df["Date"] = (
        movement_df["createdOn"].dt.date
    )

    # ========================================================
    # DAILY MOVEMENTS
    # ========================================================

    zone_daily = (
        movement_df
        .groupby(
            [
                "geozoneId",
                "Date"
            ]
        )
        .size()
        .reset_index(name="movement_count")
    )


    # ========================================================
    # THRESHOLD
    # ========================================================

    threshold = 20

    zone_daily["status"] = np.where(
        zone_daily["movement_count"] < threshold,
        "Underperforming",
        "Normal"
    )

    # ========================================================
    # FILTER
    # ========================================================

    zone_daily = zone_daily[
        zone_daily["status"] == "Underperforming"
    ]

    # ========================================================
    # SORT
    # ========================================================

    zone_daily = zone_daily.sort_values(
        by="movement_count",
        ascending=True
    )

    # ========================================================
    # CREATE TABLE
    # ========================================================

    create_table_query = """
    CREATE TABLE IF NOT EXISTS tbl_underperforming_geozones (
        geozoneId BIGINT,
        Date DATE,
        movement_count INT,
        status VARCHAR(50)
    )
    """

    with engine.begin() as conn:
        conn.execute(text(create_table_query))

    # ========================================================
    # CLEAR OLD DATA
    # ========================================================

    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE tbl_underperforming_geozones"
            )
        )

    # ========================================================
    # STORE RESULT
    # ========================================================

    zone_daily.to_sql(
        "tbl_underperforming_geozones",
        engine,
        if_exists="append",
        index=False
    )

    print("Underperforming Geozones Stored")