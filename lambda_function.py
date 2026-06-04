import json
import joblib
import boto3
import pandas as pd
from predictor import generate_prediction_dataframe
from db import get_geozones, save_forecasts, truncate_forecast_table


MODEL_PATH = "/tmp/model.pkl"

s3 = boto3.client("s3")


def load_model():

    s3.download_file(
        "demand-forecast-model-bucket",
        "Stracker_randomforest_model_demand_forest.pkl",
        MODEL_PATH
    )

    return joblib.load(MODEL_PATH)


def lambda_handler(event, context):

    start_date = event["start_date"]

    if "days" in event:

        days = int(event["days"])

        end_date = (
            pd.to_datetime(start_date)
            + pd.Timedelta(days=days - 1)
        ).strftime("%Y-%m-%d")

    else:

        end_date = event.get(
            "end_date",
            start_date
        )

    model = load_model()

    geozones = get_geozones()

    pred_df = generate_prediction_dataframe(
        start_date,
        end_date,
        geozones
    )

    feature_cols = [
        "day_num",
        "is_weekend",
        "hour",
        "geozoneId",
        "geolayerId",
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
    pred_df["timestamp"] = (
        pd.to_datetime(pred_df["forecast_date"])
        + pd.to_timedelta(pred_df["hour"], unit="h")
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Current UTC timestamp
    pred_df["createdOn"] = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    

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

    # Delete old forecasts
    truncate_forecast_table()

    # Store fresh forecasts
    save_forecasts(save_df)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "rows_created": len(save_df),
            "start_date": start_date,
            "end_date": end_date
        })
    }