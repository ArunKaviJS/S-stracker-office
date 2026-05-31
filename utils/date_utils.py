from datetime import datetime


def build_date_features(date):

    return {
        "day": date.day,
        "month": date.month,
        "day_of_week": date.weekday()
    }