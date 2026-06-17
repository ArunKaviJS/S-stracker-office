import pandas as pd
import numpy as np

from reason_mapper import map_reason

def build_predictions(
    df,
    model,
    type_encoder,
    reason_encoder
):

    latest = (
        df.sort_values("createdOn")
        .groupby(
            [
                "trolleyId",
                "trolleyName",
                "serialNo",
                "reason"
            ],
            as_index=False
        )
        .last()
    )

    latest["reason"] = latest["reason"].apply(
        map_reason
    )

    MAJOR_REASONS = {
        "Accident",
        "Broken & Needs Welding",
        "Frame Damage",
        "Motor Failure",
        "Structural Damage"
    }

    latest.loc[
        latest["reason"].isin(MAJOR_REASONS),
        "type"
    ] = "Major"

    latest.loc[
        ~latest["reason"].isin(MAJOR_REASONS),
        "type"
    ] = "Minor"

    latest["createdOn"] = pd.to_datetime(
        latest["createdOn"]
    )

    latest["day"] = latest["createdOn"].dt.day
    latest["month"] = latest["createdOn"].dt.month
    latest["day_of_week"] = latest["createdOn"].dt.dayofweek

    latest["type"] = type_encoder.transform(
        latest["type"]
    )

    latest["reason"] = reason_encoder.transform(
        latest["reason"]
    )

    X = latest[
        [
            "trolleyId",
            "type",
            "reason",
            "day",
            "month",
            "day_of_week"
        ]
    ]

    preds = model.predict(X)

    preds = np.round(preds).astype(int)

    latest["untilnextday"] = preds

    latest["nextmaintenancedate"] = (
        latest["createdOn"] +
        pd.to_timedelta(preds, unit="D")
    )

    return latest


def filter_predictions(
    pred_df,
    start_date,
    end_date
):

    start_date = pd.to_datetime(start_date)

    end_date = pd.to_datetime(end_date)

    return pred_df[
        (
            pred_df["nextmaintenancedate"]
            >= start_date
        )
        &
        (
            pred_df["nextmaintenancedate"]
            <= end_date
        )
    ]