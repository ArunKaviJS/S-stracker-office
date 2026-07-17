import json

from sqlalchemy import text

from db import get_engine


def create_response_table():

    engine = get_engine()

    with engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tbl_chat_response (
            chatId    BIGINT PRIMARY KEY AUTO_INCREMENT,
            userId    VARCHAR(255),
            question  TEXT,
            sqlQuery LONGTEXT,
            intent    VARCHAR(50),
            chatTitle TEXT,
            response  LONGTEXT,
            createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))


def save_response(
    user_id,
    question,
    sql_query,
    intent,
    chat_title,
    response
):
    """
    Persist one chat turn to tbl_chat_response.

    response may be None, a dict/list (stored as JSON), or a plain string (S3 URL).
    """
    print('**************saving response...*********************')
    engine = get_engine()

    if response is None:
        response_value = None
    elif isinstance(response, str):
        response_value = response
    else:
        response_value = json.dumps(response, default=str)

    
    print(chat_title)
    print('************************************')
    with engine.begin() as conn:

        conn.execute(text("""
        INSERT INTO tbl_chat_response
            (userId, question, sqlQuery, intent, chatTitle, response)
        VALUES
            (:userId, :question, :sqlQuery, :intent, :chatTitle, :response)
        """), {
            "userId":    user_id,
            "question":   question,
            "sqlQuery":  sql_query,
            "intent":     intent,
            "chatTitle": chat_title,
            "response":   response_value
        })
