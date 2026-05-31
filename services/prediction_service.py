import pandas as pd

from utils.date_utils import build_date_features


def predict_range(
    latest_df,
    start_date,
    end_date,
    model,
    type_encoder,
    reason_encoder
):

    prediction_rows = []

    current_date = start_date

    while current_date <= end_date:

        features = build_date_features(
            current_date
        )

        for _, row in latest_df.iterrows():

            X = pd.DataFrame([{
                "trolleyId": row["trolleyId"],
                "type": type_encoder.transform(
                    [row["type"]]
                )[0],
                "reason": reason_encoder.transform(
                    [row["reason"]]
                )[0],
                "day": features["day"],
                "month": features["month"],
                "day_of_week": features["day_of_week"]
            }])

            predicted_days = int(
                round(
                    model.predict(X)[0]
                )
            )

            next_maintenance = (
                current_date +
                pd.Timedelta(days=predicted_days)
            )

            prediction_rows.append({
                "prediction_date": current_date,
                "trolleyId": row["trolleyId"],
                "type": row["type"],
                "reason": row["reason"],
                "predicted_days": predicted_days,
                "next_maintenance_date":
                    next_maintenance
            })

        current_date += pd.Timedelta(days=1)

    return pd.DataFrame(prediction_rows)