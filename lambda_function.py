import json
import joblib
import boto3

from predictor import generate_prediction_dataframe
from db import get_geozones, save_forecasts


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

    save_df = pred_df[
        [
            "forecast_date",
            "hour",
            "geozoneId",
            "geolayerId",
            "predicted_trolley_count"
        ]
    ].copy()

    save_df.rename(
        columns={
            "hour": "forecast_hour"
        },
        inplace=True
    )

    save_forecasts(save_df)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "rows_created": len(save_df),
            "start_date": start_date,
            "end_date": end_date
        })
    }