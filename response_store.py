import json

from sqlalchemy import text

from db import get_engine


def create_response_table():

    engine = get_engine()

    with engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tbl_chat_response (
            ChatId    BIGINT PRIMARY KEY AUTO_INCREMENT,
            UserId    VARCHAR(255),
            question  TEXT,
            sql_query LONGTEXT,
            Intent    VARCHAR(50),
            Chat_title TEXT,
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

    engine = get_engine()

    if response is None:
        response_value = None
    elif isinstance(response, str):
        response_value = response
    else:
        response_value = json.dumps(response, default=str)

    with engine.begin() as conn:

        conn.execute(text("""
        INSERT INTO tbl_chat_response
            (UserId, question, sql_query, Intent, Chat_title, response)
        VALUES
            (:user_id, :question, :sql_query, :intent, :chat_title, :response)
        """), {
            "user_id":    user_id,
            "question":   question,
            "sql_query":  sql_query,
            "intent":     intent,
            "chat_title": chat_title,
            "response":   response_value
        })
