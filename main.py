import json
from concurrent.futures import ThreadPoolExecutor

from llm import generate_sql, detect_intent
from db import execute_query
from router import route
from sql_guard import validate_sql, BlockedQueryError
from response_store import create_response_table, save_response


def run(question, user_id):
    
    print('***********Question**********')
    print(question)
    print('*****************************')

    create_response_table()


    # LLM call 1 & 2 in parallel: SQL generation + intent detection
    sql = None
    try:
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            sql_future    = executor.submit(generate_sql, question)
            intent_future = executor.submit(detect_intent, question)
            sql    = sql_future.result()
            intent = intent_future.result()
        print('***************Intent********************')
        print( intent)
        print('*****************************************')
        validate_sql(sql, user_id=user_id, question=question)

    except BlockedQueryError as e:
        print("Blocked query detected:", e)
        blocked_result = {
            "intent": "sql_error",
            "chatTitle": "I have no permission to execute database operations that modify data or schema, including DROP, DELETE, ALTER, TRUNCATE, INSERT, and UPDATE.",
            "response": None
        }
        return blocked_result


    # Main flow — retry up to 3 times (regenerate SQL on each failure)
    df = None
    last_error = None
    for attempt in range(1, 4):
        try:
            print(f'********executed query (attempt {attempt})**********')
            df = execute_query(sql)
            print(df)
            print('********************************')
            break  # success — exit retry loop
        except Exception as e:
            last_error = e
            print(f'SQL execution error (attempt {attempt}):', e)
            if attempt < 3:
                print(f'Regenerating SQL for attempt {attempt + 1}...')
                sql = generate_sql(question)
                validate_sql(sql, user_id=user_id, question=question)

    if df is None:
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
    question = input("Question: ").strip()
    user_id = input("User ID: ").strip()

    result = run(question, user_id)
    print(json.dumps(result, indent=2, default=str))
