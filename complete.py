import os
import pandas as pd
import numpy as np

from sqlalchemy import create_engine, text

# ============================================================
# DB 1 -> SOURCE DATABASE
# ============================================================

SOURCE_HOST = os.getenv("SOURCE_DB_HOST")
SOURCE_USER = os.getenv("SOURCE_DB_USER")
SOURCE_PASSWORD = os.getenv("SOURCE_DB_PASSWORD")
SOURCE_DATABASE = os.getenv("SOURCE_DB_NAME")

# ============================================================
# DB 2 -> DESTINATION DATABASE
# ============================================================

DEST_HOST = os.getenv("DEST_DB_HOST")
DEST_USER = os.getenv("DEST_DB_USER")
DEST_PASSWORD = os.getenv("DEST_DB_PASSWORD")
DEST_DATABASE = os.getenv("DEST_DB_NAME")

# ============================================================
# SQLALCHEMY CONNECTIONS
# ============================================================

source_engine = create_engine(
    f"mysql+pymysql://{SOURCE_USER}:{SOURCE_PASSWORD}@{SOURCE_HOST}:3306/{SOURCE_DATABASE}"
)

dest_engine = create_engine(
    f"mysql+pymysql://{DEST_USER}:{DEST_PASSWORD}@{DEST_HOST}:3306/{DEST_DATABASE}"
)

print("Connected Successfully!")

# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):

    try:

        # ====================================================
        # STEP 1 -> CREATE TRACKER TABLE IF NOT EXISTS
        # ====================================================

        create_tracker_query = """
        CREATE TABLE IF NOT EXISTS sync_tracker (
            process_name VARCHAR(100) PRIMARY KEY,
            last_processed_id BIGINT
        )
        """

        with dest_engine.begin() as conn:
            conn.execute(text(create_tracker_query))

        # ====================================================
        # STEP 2 -> INSERT INITIAL VALUE
        # ====================================================

        insert_initial_query = """
        INSERT IGNORE INTO sync_tracker (
            process_name,
            last_processed_id
        )
        VALUES (
            'tbl_device_history_sync',
            0
        )
        """

        with dest_engine.begin() as conn:
            conn.execute(text(insert_initial_query))

        # ====================================================
        # STEP 3 -> GET LAST FETCHED ID
        # ====================================================

        last_id_query = """
        SELECT last_processed_id
        FROM sync_tracker
        WHERE process_name = 'tbl_device_history_sync'
        """

        last_processed_id = pd.read_sql(
            last_id_query,
            dest_engine
        ).iloc[0]["last_processed_id"]

        print(f"Last Processed ID : {last_processed_id}")

        # ====================================================
        # STEP 4 -> FETCH ONLY NEW DATA FROM DB1
        # ====================================================

        fetch_new_query = f"""
        SELECT *
        FROM tbl_device_history
        WHERE id > {last_processed_id}
        ORDER BY id ASC
        """

        new_data = pd.read_sql(
            fetch_new_query,
            source_engine
        )

        # ====================================================
        # STEP 5 -> IF NO NEW DATA
        # ====================================================

        if new_data.empty:

            return {
                "statusCode": 200,
                "message": "No New Data Found"
            }

        print(f"New Rows : {len(new_data)}")

        # ====================================================
        # STEP 6 -> STORE NEW DATA INTO DB2
        # ====================================================

        new_data.to_sql(
            "tbl_device_history",
            dest_engine,
            if_exists="append",
            index=False
        )

        print("New Data Stored into DB2")

        # ====================================================
        # STEP 7 -> LOAD COMPLETE DATA FROM DB2
        # ====================================================

        df = pd.read_sql(
            "SELECT * FROM tbl_device_history",
            dest_engine
        )

        # ====================================================
        # ====================================================
        # KPI 1 -> IDLE TROLLEYS
        # ====================================================
        # ====================================================

        df1 = df[[
            "trolleyId",
            "geozoneId",
            "createdOn",
            "status"
        ]].copy()

        # ====================================================
        # DATETIME CONVERSION
        # ====================================================

        df1["createdOn"] = pd.to_datetime(
            df1["createdOn"],
            errors="coerce"
        )

        # ====================================================
        # REMOVE NULLS
        # ====================================================

        df1 = df1.dropna(
            subset=[
                "trolleyId",
                "geozoneId",
                "createdOn"
            ]
        )

        # ====================================================
        # REMOVE DUPLICATES
        # ====================================================

        df1 = df1.drop_duplicates(
            subset=[
                "trolleyId",
                "geozoneId",
                "createdOn"
            ]
        )

        # ====================================================
        # SORT DATA
        # ====================================================

        df1 = df1.sort_values(
            by=[
                "trolleyId",
                "createdOn"
            ]
        ).reset_index(drop=True)

        # ====================================================
        # DETECT GEOZONE CHANGE
        # ====================================================

        df1["prev_geozone"] = (
            df1.groupby("trolleyId")["geozoneId"]
            .shift(1)
        )

        df1["zone_changed"] = (
            df1["geozoneId"] != df1["prev_geozone"]
        )

        # ====================================================
        # CREATE STREAK GROUPS
        # ====================================================

        df1["streak_id"] = (
            df1.groupby("trolleyId")["zone_changed"]
            .cumsum()
        )

        # ====================================================
        # CALCULATE STREAKS
        # ====================================================

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

        # ====================================================
        # IDLE HOURS
        # ====================================================

        streaks["idle_hours"] = (
            (
                streaks["end_time"] -
                streaks["start_time"]
            )
            .dt.total_seconds() / 3600
        )

        # ====================================================
        # IDLE STATUS
        # ====================================================

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

        # ====================================================
        # FILTER ONLY REQUIRED STATUS
        # ====================================================

        idle_trolleys = streaks[
            streaks["idle_status"].isin(
                [
                    "Idle",
                    "Severe",
                    "Critical"
                ]
            )
        ]

        # ====================================================
        # FINAL COLUMNS
        # ====================================================

        idle_trolleys = idle_trolleys[
            [
                "trolleyId",
                "geozoneId",
                "idle_hours",
                "idle_status"
            ]
        ]

        # ====================================================
        # SORT
        # ====================================================

        idle_trolleys = idle_trolleys.sort_values(
            by="idle_hours",
            ascending=False
        )

        # ====================================================
        # CREATE TABLE
        # ====================================================

        create_idle_table = """
        CREATE TABLE IF NOT EXISTS tbl_idle_trolleys (
            trolleyId BIGINT,
            geozoneId BIGINT,
            idle_hours FLOAT,
            idle_status VARCHAR(50)
        )
        """

        with dest_engine.begin() as conn:
            conn.execute(text(create_idle_table))

        # ====================================================
        # CLEAR OLD DATA
        # ====================================================

        with dest_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE tbl_idle_trolleys"))

        # ====================================================
        # STORE RESULT
        # ====================================================

        idle_trolleys.to_sql(
            "tbl_idle_trolleys",
            dest_engine,
            if_exists="append",
            index=False
        )

        print("Idle Trolleys Stored")

        # ====================================================
        # ====================================================
        # KPI 2 -> UNDERPERFORMING GEOZONES
        # ====================================================
        # ====================================================

        df2 = df.copy()

        # ====================================================
        # SORT
        # ====================================================

        df2 = df2.sort_values(
            by=[
                "trolleyId",
                "createdOn"
            ]
        ).reset_index(drop=True)

        # ====================================================
        # PREVIOUS GEOZONE
        # ====================================================

        df2["prev_geozone"] = (
            df2.groupby("trolleyId")["geozoneId"]
            .shift(1)
        )

        df2["zone_changed"] = (
            df2["geozoneId"] != df2["prev_geozone"]
        )

        # ====================================================
        # MOVEMENTS ONLY
        # ====================================================

        movement_df = df2[
            df2["zone_changed"] == True
        ].copy()

        # ====================================================
        # DATETIME
        # ====================================================

        movement_df["createdOn"] = pd.to_datetime(
            movement_df["createdOn"],
            errors="coerce"
        )

        movement_df["Date"] = (
            movement_df["createdOn"].dt.date
        )

        # ====================================================
        # DAILY COUNT
        # ====================================================

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

        # ====================================================
        # THRESHOLD
        # ====================================================

        threshold = 20

        zone_daily["status"] = np.where(
            zone_daily["movement_count"] < threshold,
            "Underperforming",
            "Normal"
        )

        # ====================================================
        # FILTER ONLY UNDERPERFORMING
        # ====================================================

        zone_daily = zone_daily[
            zone_daily["status"] == "Underperforming"
        ]

        # ====================================================
        # SORT
        # ====================================================

        zone_daily = zone_daily.sort_values(
            by="movement_count",
            ascending=True
        )

        # ====================================================
        # CREATE TABLE
        # ====================================================

        create_zone_table = """
        CREATE TABLE IF NOT EXISTS tbl_underperforming_geozones (
            geozoneId BIGINT,
            Date DATE,
            movement_count INT,
            status VARCHAR(50)
        )
        """

        with dest_engine.begin() as conn:
            conn.execute(text(create_zone_table))

        # ====================================================
        # CLEAR OLD DATA
        # ====================================================

        with dest_engine.begin() as conn:
            conn.execute(
                text("TRUNCATE TABLE tbl_underperforming_geozones")
            )

        # ====================================================
        # STORE RESULT
        # ====================================================

        zone_daily.to_sql(
            "tbl_underperforming_geozones",
            dest_engine,
            if_exists="append",
            index=False
        )

        print("Underperforming Geozones Stored")

        # ====================================================
        # STEP 8 -> UPDATE LAST FETCHED ID
        # ====================================================

        new_last_id = int(new_data["id"].max())

        update_query = f"""
        UPDATE sync_tracker
        SET last_processed_id = {new_last_id}
        WHERE process_name = 'tbl_device_history_sync'
        """

        with dest_engine.begin() as conn:
            conn.execute(text(update_query))

        print("Tracker Updated")

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "statusCode": 200,
            "message": "Success",
            "new_rows_processed": len(new_data),
            "last_processed_id": new_last_id
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "error": str(e)
        }