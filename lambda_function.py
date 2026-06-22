import json

from llm import generate_sql, get_client
from db import execute_query
from router import route
from config import AZURE_OPENAI_DEPLOYMENT
from sql_guard import validate_sql
from response_store import create_response_table, save_response


def lambda_handler(event, context):

    try:

        body = event

        if "body" in event:
            body = json.loads(event["body"])

        question = body.get("question", "")
        user_id  = body.get("userId", "")

        create_response_table()

        # SQL generation — fallback stored and returned on failure
        try:
            sql = generate_sql(question)
            validate_sql(sql)
        except Exception:
            sql_error_result = {
                "intent": "sql_error",
                "chat_title": "I could not interpret that question",
                "response": None
            }
            save_response(
                user_id=user_id,
                question=question,
                sql_query=None,
                intent=sql_error_result["intent"],
                chat_title=sql_error_result["chat_title"],
                response=sql_error_result["response"]
            )
            return {
                "statusCode": 200,
                "body": json.dumps(sql_error_result)
            }

        # Main flow
        df = execute_query(sql)

        result = route(
            question,
            df,
            get_client(),
            AZURE_OPENAI_DEPLOYMENT
        )

        save_response(
            user_id=user_id,
            question=question,
            sql_query=sql,
            intent=result["intent"],
            chat_title=result["chat_title"],
            response=result["response"]
        )

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str)
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "body": json.dumps({
                "intent": "error",
                "message": str(e)
            })
        }
