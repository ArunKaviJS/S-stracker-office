import json
import joblib
import boto3
import pandas as pd
from predictor import generate_prediction_dataframe
from db import (
    get_geozones,
    save_forecasts,
    get_latest_forecast_date,
    delete_expired_forecasts
)



MODEL_PATH = "/tmp/model.pkl"

s3 = boto3.client("s3")


def load_model():

    s3.download_file(
        "demand-forecast-model-bucket",
        "rf_trolley_model.pkl",
        MODEL_PATH
    )

    return joblib.load(MODEL_PATH)


def lambda_handler(event, context):
    
   

    latest_date = get_latest_forecast_date()

    today = pd.Timestamp.now().normalize()

    # Forecast table empty
    if latest_date is None or pd.isna(latest_date):

        start_date = today
        end_date = today + pd.Timedelta(days=9)

    # Forecast table has data
    else:

        start_date = (
            pd.to_datetime(latest_date)
            + pd.Timedelta(days=1)
        )

        end_date = start_date

    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    model = load_model()

    geozones = get_geozones()
    
    print("Geozone rows:", len(geozones))
    print("Unique geozones:", geozones["geozoneId"].nunique())
    print(sorted(geozones["geozoneId"].unique()))
    
    pred_df = generate_prediction_dataframe(
        start_date,
        end_date,
        geozones
    )
    
    print("Rows:", len(pred_df))

    print(
        pred_df.groupby(
            ["forecast_date", "hour", "geozoneId"]
        ).size().max()
    )

    feature_cols = [
        "day_num",
        "is_weekend",
        "hour",
        "geozoneId",
        "month",
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
        "day_sin",
        "day_cos"
    ]

    pred_df["predicted_trolley_count"] = (
        model.predict(pred_df[feature_cols])
        .clip(0)
        .round()
        .astype(int)
    )
    
    

    # Combine forecast_date + hour into ISO timestamp
    # Forecast timestamp
    pred_df["timestamp"] = (
        pd.to_datetime(pred_df["forecast_date"])
        + pd.to_timedelta(pred_df["hour"], unit="h")
    )

    # Current UTC timestamp
    pred_df["createdOn"] = pd.Timestamp.utcnow()
    

    save_df = pred_df[
        [
            "forecast_date",
            "hour",
            "timestamp",
            "geozoneId",
            "geozoneName",
            "predicted_trolley_count",
            "createdOn"
        ]
    ].copy()
     
     
     
    save_df.rename(
        columns={
            "hour": "forecast_hour"
        },
        inplace=True
    )

    save_df["timestamp"] = pd.to_datetime(save_df["timestamp"])
    save_df["createdOn"] = pd.to_datetime(save_df["createdOn"])
    
    #======================temporory for UI=======================
    # --------------------------------------------------
    # Geozone ID Mapping
    # 1 -> 47, 2 -> 48, ..., 24 -> 70
    # --------------------------------------------------

    GEOZONE_ID_MAPPING = {
        1: 47,
        2: 48,
        3: 49,
        4: 50,
        5: 51,
        6: 52,
        7: 53,
        8: 54,
        9: 55,
        10: 56,
        11: 57,
        12: 58,
        13: 59,
        14: 60,
        15: 61,
        16: 62,
        17: 63,
        18: 64,
        19: 65,
        20: 66,
        21: 67,
        22: 68,
        23: 69,
        24: 70,
    }


    save_df["geozoneId"] = save_df["geozoneId"].map(GEOZONE_ID_MAPPING)
    
    
    # --------------------------------------------------
    # Geozone Name Mapping
    # Based on the order shown in the image
    # --------------------------------------------------

    GEOZONE_NAME_MAPPING = {
        "MTB LEVEL 2": "Dummy Geozone",
        "STCP BLOCK A LEVEL 5": "MTB Level 5",
        "STCP BLOCK B LEVEL 5": "Ap Geozones",
        "STCP BLOCK A LEVEL 4": "Postgraduate Lounge",
        "STCP BLOCK B LEVEL 4": "Japanese Language Centre",
        "STCP BLOCK A LEVEL 3": "Mizan Research Centre",
        "STCP BLOCK B LEVEL 3": "Third Floor Lift",
        "STCP BLOCK A LEVEL 2": "Restroom",
        "STCP BLOCK B LEVEL 2": "LATLONG 1",
        "STCP BLOCK A LEVEL 1": "LATLONG2",
        "STCP BLOCK B LEVEL 1": "LATLONG3",
        "STCP BLOCK A LEVEL G": "LATLONG4",
        "STCP BLOCK B LEVEL G": "LATLONG5",
        "STCP BLOCK A LEVEL B": "LATLONG6",
        "STCP BLOCK B LEVEL B": "LATLONG7",
        "MTB LEVEL 3": "ARJUN-GEOZONE-1",
        "MTB LEVEL 3 MAINTENANCE 1": "ARJUN-GEOZONE-2",
        "MTB LEVEL 5": "ARJUN-GEOZONE-3",
        "MTB LEVEL 5 CLEANING": "ARJUN-GEOZONE-4",
        "Firmware Zone MTB Level 2": "ARJUN-GEOZONE-5",
        "Firmware Zone": "ARJUN-GEOZONE-6",
        "Lobby Zone": "ARJUN-GEOZONE-7",
        "STCP BLOCK A": "ARJUN-GEOZONE-8",
        "MTB LEVEL 3 MAINTENANCE 2": "ARJUN-GEOZONE-9",
    }


    save_df["geozoneName"] = save_df["geozoneName"].replace(GEOZONE_NAME_MAPPING)
    
    #======================temporory for UI=======================
    
    # Store fresh forecasts
    save_forecasts(save_df)

    delete_expired_forecasts()
    
    #delete expired date from db
    return {
        "statusCode": 200,
        "body": json.dumps({
            "rows_created": len(save_df),
            "start_date": start_date,
            "end_date": end_date
        })
    }