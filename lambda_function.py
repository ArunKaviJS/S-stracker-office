import json
import pandas as pd

from services.s3_service import (
    download_latest_model
)

from services.model_service import (
    load_model
)

from services.db_service import (
    get_latest_maintenance_data,
    insert_predictions
)

from services.prediction_service import (
    predict_range
)

from utils.logger import log


def lambda_handler(event, context):

    try:

        log("Lambda Started")

        start_date = pd.to_datetime(
            event["start_date"]
        )

        end_date = pd.to_datetime(
            event["end_date"]
        )

        download_latest_model()

        (
            model,
            type_encoder,
            reason_encoder
        ) = load_model()

        latest_df = (
            get_latest_maintenance_data()
        )

        result_df = predict_range(
            latest_df,
            start_date,
            end_date,
            model,
            type_encoder,
            reason_encoder
        )

        insert_predictions(result_df)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message":
                    "Prediction completed",
                "rows_inserted":
                    len(result_df)
            })
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }