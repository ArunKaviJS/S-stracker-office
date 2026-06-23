import boto3
import uuid
from io import BytesIO, StringIO

from config import S3_BUCKET_NAME

s3 = boto3.client("s3")

BUCKET_NAME = S3_BUCKET_NAME


def upload_dataframe_to_s3(df):
    """Upload df as CSV and return a presigned URL."""
    print("Upload df as CSV and return a presigned URL.")
    csv_buffer = StringIO()

    df.to_csv(csv_buffer, index=False)

    file_key = f"query-results/{uuid.uuid4()}.csv"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_key,
        Body=csv_buffer.getvalue(),
        ContentType="text/csv"
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": file_key},
        ExpiresIn=86400
    )
    print('S3_URL',url)
    return url


def upload_dataframe_to_s3_xlsx(df):
    """Upload df as XLSX and return a presigned URL."""
    print('Upload df as XLSX ')
    xlsx_buffer = BytesIO()

    df.to_excel(xlsx_buffer, index=False, engine="openpyxl")

    xlsx_buffer.seek(0)

    file_key = f"query-results/{uuid.uuid4()}.xlsx"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_key,
        Body=xlsx_buffer.getvalue(),
        ContentType=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        )
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": file_key},
        ExpiresIn=86400
    )
    print("xlsx url",url)
    return url
