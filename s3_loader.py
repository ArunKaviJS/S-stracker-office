import boto3
import joblib
import io
import os

BUCKET_NAME = os.environ['BUCKET_NAME']

s3 = boto3.client("s3")


def load_pickle(key):

    obj = s3.get_object(
        Bucket=BUCKET_NAME,
        Key=key
    )

    return joblib.load(
        io.BytesIO(
            obj["Body"].read()
        )
    )


def load_model():

    return load_pickle(
        "model.pkl"
    )


def load_type_encoder():

    return load_pickle(
        "type_encoder.pkl"
    )


def load_reason_encoder():

    return load_pickle(
        "reason_encoder.pkl"
    )