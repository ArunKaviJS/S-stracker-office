import json
import os
import pymysql
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

def lambda_handler(event, context):
    # Parse userId from body
    try:
        user_id = event.get("userId")
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid request body", "details": str(e)})
        }

    if not user_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "userId is required"})
        }

    connection = None
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )

        with connection.cursor() as cursor:
            query = """
                SELECT ChatId, question
                FROM tbl_chat_response
                WHERE UserId = %s
                ORDER BY createdAt DESC
                LIMIT 5
            """
            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

        if not rows:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "userId": user_id,
                    "count": 0,
                    "chats": []
                })
            }

        # Reverse to return in ascending order (oldest first)
        rows = list(reversed(rows))

        return {
            "statusCode": 200,
            "body": json.dumps({
                "userId": user_id,
                "count": len(rows),
                "chats": rows
            })
        }

    except pymysql.MySQLError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Database error", "details": str(e)})
        }

    finally:
        if connection:
            connection.close()