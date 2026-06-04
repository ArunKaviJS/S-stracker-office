import pandas as pd
import numpy as np


def generate_prediction_dataframe(
        start_date,
        end_date,
        geozones
):

    rows = []

    current = pd.Timestamp(start_date)

    while current <= pd.Timestamp(end_date):

        for _, gz in geozones.iterrows():

            for hr in range(24):

                rows.append({

                    "forecast_date": current.date(),

                    "day_num": current.dayofweek,

                    "is_weekend": int(current.dayofweek >= 5),

                    "hour": hr,

                    "geozoneId": gz["geozoneId"],

                    "geolayerId": gz["geolayerId"],
                    
                    # NEW
                    "geozoneName": gz["geozoneName"],

                    "month": current.month,

                    "hour_sin": np.sin(2*np.pi*hr/24),
                    "hour_cos": np.cos(2*np.pi*hr/24),

                    "month_sin": np.sin(2*np.pi*current.month/12),
                    "month_cos": np.cos(2*np.pi*current.month/12),

                    "day_sin": np.sin(2*np.pi*current.dayofweek/7),
                    "day_cos": np.cos(2*np.pi*current.dayofweek/7)

                })

        current += pd.Timedelta(days=1)

    return pd.DataFrame(rows)