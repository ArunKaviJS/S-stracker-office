import json

from llm import (
    generate_sql,
    get_client
)

from db import execute_query

from router import route

from config import AZURE_OPENAI_DEPLOYMENT

from sql_guard import validate_sql


from response_store import (
    create_response_table,
    truncate_response_table,
    save_response
)

def lambda_handler(event, context):

    try:

        body = event

        if "body" in event:

            body = json.loads(event["body"])

        question = body["question"]

        sql = generate_sql(question)

        validate_sql(sql)


        df = execute_query(sql)

        result = route(
            question,
            df,
            get_client(),
            AZURE_OPENAI_DEPLOYMENT
        )

        result["sql_query"] = sql
        
        create_response_table()

        truncate_response_table()

        save_response(
            question,
            sql,
            result
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                result,
                default=str
            )
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "body": json.dumps({
                "response_type": "error",
                "message": str(e)
            })
        }