import os
import json
from sqlalchemy import create_engine
from Idle_Trolleys_Logic import process_idle_trolleys
from Geozone_Performance_Logic import process_underperforming_geozones

# ============================================================
# SOURCE DB
# ============================================================

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_NAME")

# ============================================================
# SQLALCHEMY CONNECTIONS
# ============================================================

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_DATABASE}"
)

# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    try:

        # ============================================
        # PROCESS IDLE TROLLEYS
        # ============================================

        process_idle_trolleys(engine)

        # ============================================
        # PROCESS UNDERPERFORMING GEOZONES
        # ============================================

        process_underperforming_geozones(engine)

        # ============================================
        # SUCCESS RESPONSE
        # ============================================

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "message": "Processing completed successfully"
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "failed",
                "error": str(e)
            })
        }