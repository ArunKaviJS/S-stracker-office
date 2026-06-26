import pandas as pd
import numpy as np

from reason_mapper import map_reason

MAJOR_REASONS = {
    "Accident",
    "Broken & Needs Welding",
    "Frame Damage",
    "Motor Failure",
    "Structural Damage"
}


def build_predictions(
    df,
    model,
    type_encoder,
    reason_encoder
):

    # Step 1: Map reason and derive type on ALL records first
    df = df.copy()

    df["reason"] = df["reason"].apply(map_reason)

    df.loc[df["reason"].isin(MAJOR_REASONS), "type"] = "major"
    df.loc[~df["reason"].isin(MAJOR_REASONS), "type"] = "minor"

    # Step 2: Get last maintenance per trolley per reason
    df["createdOn"] = pd.to_datetime(df["createdOn"], format="%d-%m-%Y %H:%M")

    latest = (
        df.sort_values("createdOn")
        .groupby(
            [
                "trolleyId",
                "trolleyName",
                "serialNo",
                "reason",
                "type"
            ],
            as_index=False
        )
        .last()
    )

    print(f"Trolley-Reason breakdown:\n{latest.groupby(['trolleyName', 'reason']).size().to_string()}")
    print(f"Total trolley-reason combinations : {len(latest)}")

    # Step 3: Date features
    latest["day"] = latest["createdOn"].dt.day
    latest["month"] = latest["createdOn"].dt.month
    latest["day_of_week"] = latest["createdOn"].dt.dayofweek

    # Step 4: Encode
    latest["type"] = type_encoder.transform(latest["type"])
    latest["reason"] = reason_encoder.transform(latest["reason"])

    # Step 5: Predict
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


