import os

from sqlalchemy import create_engine

from fetch_data_and_copy import fetch_and_copy_data

from Idle_Trolleys_Logic import process_idle_trolleys

from Geozone_Performance_Logic import (
    process_underperforming_geozones
)

from fastapi import FastAPI
from mangum import Mangum



app = FastAPI()


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

@app.get("/Stracter_ai_dev")
def Stracter_ai_dev():

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
            "status": "success",
            "message": "Processing completed successfully"
        }

    except Exception as e:

        return {
            "status": "failed",
            "error": str(e)
        }
        
        
# ============================================================
# AWS LAMBDA HANDLER
# ============================================================

lambda_handler = Mangum(app)