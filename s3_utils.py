import boto3
import uuid
from io import StringIO

s3 = boto3.client("s3")

BUCKET_NAME = "ai-smart-tracker-chatbot-bitbucket"


def upload_dataframe_to_s3(df):

    csv_buffer = StringIO()

    df.to_csv(
        csv_buffer,
        index=False
    )

    file_key = (
        f"query-results/"
        f"{uuid.uuid4()}.csv"
    )

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_key,
        Body=csv_buffer.getvalue(),
        ContentType="text/csv"
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": file_key
        },
        ExpiresIn=86400
    )

    return url