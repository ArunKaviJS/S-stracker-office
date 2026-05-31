import boto3

from config.settings import *
from utils.logger import log

s3 = boto3.client("s3")


def download_latest_model():

    log("Downloading latest model files")

    s3.download_file(
        MODEL_BUCKET,
        MODEL_KEY,
        LOCAL_MODEL
    )

    s3.download_file(
        MODEL_BUCKET,
        TYPE_ENCODER_KEY,
        LOCAL_TYPE_ENCODER
    )

    s3.download_file(
        MODEL_BUCKET,
        REASON_ENCODER_KEY,
        LOCAL_REASON_ENCODER
    )

    log("Latest artifacts downloaded")