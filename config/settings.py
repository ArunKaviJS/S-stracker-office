import os

# RDS
DB_HOST = os.environ["DB_HOST"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME = os.environ["DB_NAME"]

# S3
MODEL_BUCKET = os.environ["MODEL_BUCKET"]

MODEL_KEY = "latest/model.pkl"
TYPE_ENCODER_KEY = "latest/type_encoder.pkl"
REASON_ENCODER_KEY = "latest/reason_encoder.pkl"

LOCAL_MODEL = "/tmp/model.pkl"
LOCAL_TYPE_ENCODER = "/tmp/type_encoder.pkl"
LOCAL_REASON_ENCODER = "/tmp/reason_encoder.pkl"