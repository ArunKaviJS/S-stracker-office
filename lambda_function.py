import json
import pandas as pd

from db import (
    load_latest_maintenance,
    save_predictions
)

from predictor import (
    build_predictions
)

from s3_loader import (
    load_model,
    load_type_encoder,
    load_reason_encoder
)

# ---------------------------------------------------
# Load once during Lambda cold start
# ---------------------------------------------------

MODEL = load_model()
TYPE_ENCODER = load_type_encoder()
REASON_ENCODER = load_reason_encoder()


# ---------------------------------------------------
# Lambda Handler
# ---------------------------------------------------

def lambda_handler(event, context):

    try:

        print("=" * 80)
        print("PREDICTIVE MAINTENANCE LAMBDA STARTED")
        print("=" * 80)


        # ---------------------------------------------------
        # Load maintenance data
        # ---------------------------------------------------

        raw_df = load_latest_maintenance()

        print(f"Maintenance Records Loaded : {len(raw_df)}")

        if raw_df.empty:

            return {
                "statusCode": 200,
                "message": "No maintenance records found",
                "rows_inserted": 0
            }

        # ---------------------------------------------------
        # Predict
        # ---------------------------------------------------

        pred_df = build_predictions(
            df=raw_df,
            model=MODEL,
            type_encoder=TYPE_ENCODER,
            reason_encoder=REASON_ENCODER
        )

        print(f"Predictions Generated : {(pred_df.head())}")

        if pred_df.empty:

            return {
                "statusCode": 200,
                "message": "No predictions found for date window",
                "rows_inserted": 0
            }
        
        # Decode type
        pred_df["type"] = TYPE_ENCODER.inverse_transform(
            pred_df["type"].astype(int)
        )

        # Decode reason
        pred_df["reason"] = REASON_ENCODER.inverse_transform(
            pred_df["reason"].astype(int)
        )
        
        output_df = pred_df[
            [
                "trolleyId",
                "trolleyName",
                "serialNo",
                "type",
                "reason",
                "createdOn",
                "nextmaintenancedate"
            ]
        ].copy()

        output_df.rename(
            columns={
                "trolleyId": "TrolleyId",
                "trolleyName": "TrolleyName",
                "serialNo": "SerialNo",
                "type": "Type",
                "reason": "Reason",
                "createdOn": "LastMaintanence",
                "nextmaintenancedate": "NextMaintanence"
            },
            inplace=True
        )

        # ---------------------------------------------------
        # Save to DB
        # ---------------------------------------------------

        save_predictions(output_df)

        print(f"Inserted Rows : {len(output_df)}")

        # ---------------------------------------------------
        # Response
        # ---------------------------------------------------

        return {
            "statusCode": 200,
            "message": "Prediction completed successfully",
            "rows_inserted": int(len(output_df))
        }

    except Exception as e:

        print(f"ERROR : {str(e)}")

        return {
            "statusCode": 500,
            "error": str(e)
        }