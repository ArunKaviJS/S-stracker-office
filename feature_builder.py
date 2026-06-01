import numpy as np
import pandas as pd


def build_features(date, geozoneId, geolayerId):

    dt = pd.Timestamp(date)

    day_num = dt.dayofweek

    return {
        "day_num": day_num,
        "is_weekend": int(day_num >= 5),
        "hour": None,
        "geozoneId": geozoneId,
        "geolayerId": geolayerId,
        "month": dt.month,

        "hour_sin": None,
        "hour_cos": None,

        "month_sin": np.sin(2*np.pi*dt.month/12),
        "month_cos": np.cos(2*np.pi*dt.month/12),

        "day_sin": np.sin(2*np.pi*day_num/7),
        "day_cos": np.cos(2*np.pi*day_num/7)
    }