import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from llm import generate_sql, detect_intent, get_client
from db import execute_query
from router import route
from config import AZURE_OPENAI_DEPLOYMENT
from sql_guard import validate_sql, check_question, BlockedQueryError
from response_store import create_response_table, save_response


def lambda_handler(event, context):

    try:

        body = event

        if "body" in event:
            body = json.loads(event["body"])

        question = body.get("question", "")
        user_id  = body.get("userId", "")

        create_response_table()

        # Block immediately if question contains a destructive keyword
        try:
            check_question(question)
        except BlockedQueryError:
            blocked_result = {
                "intent": "sql_error",
                "chat_title": "I have no permission to execute database operations that modify data or schema, including DROP, DELETE, ALTER, TRUNCATE, INSERT, and UPDATE.",
                "response": None
            }
            save_response(
                user_id=user_id,
                question=question,
                sql_query=None,
                intent=blocked_result["intent"],
                chat_title=blocked_result["chat_title"],
                response=blocked_result["response"]
            )
            return {
                "statusCode": 200,
                "body": json.dumps(blocked_result)
            }

        # LLM call 1 & 2 in parallel: SQL generation + intent detection
        try:
            logger.info('Generating Query and Intent')
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_sql    = executor.submit(generate_sql, question)
                future_intent = executor.submit(detect_intent, question)
                sql    = future_sql.result()
                intent = future_intent.result()
            
            
            logger.info(f"Generated SQL: {sql}")   # ← ADD THIS
            logger.info(f"Detected intent: {intent}")  # ← ADD THIS
            
            validate_sql(sql)

        except BlockedQueryError:
            blocked_result = {
                "intent": "sql_error",
                "chat_title": "You are not authorised to perform this query",
                "response": None
            }
            save_response(
                user_id=user_id,
                question=question,
                sql_query=sql,
                intent=blocked_result["intent"],
                chat_title=blocked_result["chat_title"],
                response=blocked_result["response"]
            )
            return {
                "statusCode": 200,
                "body": json.dumps(blocked_result)
            }

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

        # Main flow — LLM call 3 happens inside route() only for single_line/summary
        logger.info('Executing Query')
        try:
            df = execute_query(sql)
        except Exception as sql_exec_error:
            logger.info('SQL execution error:', sql_exec_error)
            sql_error_result = {
                "intent": "sql_error",
                "chat_title": "I could not interpret that question",
                "response": None
            }
            save_response(
                user_id=user_id,
                question=question,
                sql_query=sql,
                intent=sql_error_result["intent"],
                chat_title=sql_error_result["chat_title"],
                response=sql_error_result["response"]
            )
            return {
                "statusCode": 200,
                "body": json.dumps(sql_error_result)
            }

        result = route(
            question,
            intent,
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
