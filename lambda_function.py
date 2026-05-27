import os

from sqlalchemy import create_engine

from fetch_data_and_copy import fetch_and_copy_data

from Idle_Trolleys_Logic import process_idle_trolleys

from Geozone_Performance_Logic import (
    process_underperforming_geozones
)

# ============================================================
# SOURCE DB
# ============================================================

SOURCE_HOST = os.getenv("SOURCE_DB_HOST")
SOURCE_USER = os.getenv("SOURCE_DB_USER")
SOURCE_PASSWORD = os.getenv("SOURCE_DB_PASSWORD")
SOURCE_DATABASE = os.getenv("SOURCE_DB_NAME")

# ============================================================
# DESTINATION DB
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

# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):

    try:

        # ====================================================
        # STEP 1 -> FETCH NEW DATA
        # ====================================================

        new_data_found = fetch_and_copy_data(
            source_engine,
            dest_engine
        )

        # ====================================================
        # STEP 2 -> NO NEW DATA
        # ====================================================

        if not new_data_found:

            return {
                "statusCode": 200,
                "message": "No New Data"
            }

        # ====================================================
        # STEP 3 -> IDLE TROLLEYS
        # ====================================================

        process_idle_trolleys(
            dest_engine
        )

        # ====================================================
        # STEP 4 -> UNDERPERFORMING GEOZONES
        # ====================================================

        process_underperforming_geozones(
            dest_engine
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "statusCode": 200,
            "message": "Success"
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "error": str(e)
        }