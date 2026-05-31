import joblib

from config.settings import *

_model = None
_type_encoder = None
_reason_encoder = None


def load_model():

    global _model
    global _type_encoder
    global _reason_encoder

    if _model is None:

        _model = joblib.load(LOCAL_MODEL)

        _type_encoder = joblib.load(
            LOCAL_TYPE_ENCODER
        )

        _reason_encoder = joblib.load(
            LOCAL_REASON_ENCODER
        )

    return (
        _model,
        _type_encoder,
        _reason_encoder
    )