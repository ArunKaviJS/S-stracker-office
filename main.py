import json

from llm import generate_sql, detect_intent
from db import execute_query
from router import route
from sql_guard import validate_sql, BlockedQueryError
from response_store import create_response_table, save_response


def run(question, user_id):

    create_response_table()


    # LLM call 1 & 2 in parallel: SQL generation + intent detection
    sql = None
    try:
        print('Generating Query and Intent')
        
        sql = generate_sql(question)
        intent = detect_intent(question)
        print('llm generated sql query :', sql)
        print('llm detected intent:', intent)

        validate_sql(sql, user_id=user_id, question=question)

    except BlockedQueryError as e:
        print("Blocked query detected:", e)
        blocked_result = {
            "intent": "sql_error",
            "chatTitle": "I have no permission to execute database operations that modify data or schema, including DROP, DELETE, ALTER, TRUNCATE, INSERT, and UPDATE.",
            "response": None
        }
        return blocked_result


    # Main flow
    print('Executing Query')
    try:
        df = execute_query(sql)
    except Exception as e:
        print('SQL execution error:', e)
        sql_error_result = {
            "intent": "sql_error",
            "chatTitle": "I could not interpret that question",
            "response": None
        }
        save_response(
            user_id=user_id,
            question=question,
            sql_query=sql,
            intent=sql_error_result["intent"],
            chat_title=sql_error_result["chatTitle"],
            response=sql_error_result["response"]
        )
        return sql_error_result

    result = route(question, intent, df)

    save_response(
        user_id=user_id,
        question=question,
        sql_query=sql,
        intent=result["intent"],
        chat_title=result["chatTitle"],
        response=result["response"]
    )

    return result


if __name__ == "__main__":
    question = input("delete the Table tbl_chat_response").strip()
    user_id  = input("UserId: 01 ").strip()
    result   = run(question, user_id)
    print(json.dumps(result, indent=2, default=str))
