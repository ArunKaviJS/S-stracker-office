import json

from sqlalchemy import text

from db import get_engine

def create_response_table():

    engine = get_engine()

    with engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tbl_chat_response (
            chatId BIGINT PRIMARY KEY AUTO_INCREMENT,

            question TEXT,
            sql_query LONGTEXT,

            response_type VARCHAR(20),

            response_json LONGTEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
def truncate_response_table():

    engine = get_engine()

    with engine.begin() as conn:

        conn.execute(
            text("TRUNCATE TABLE tbl_chat_response")
        )
        
def save_response(
    question,
    sql_query,
    result
):

    engine = get_engine()

    with engine.begin() as conn:

        conn.execute(text("""
        INSERT INTO tbl_chat_response
        (
            question,
            sql_query,
            response_type,
            response_json
        )
        VALUES
        (
            :question,
            :sql_query,
            :response_type,
            :response_json
        )
        """), {

            "question":
            question,

            "sql_query":
            sql_query,

            "response_type":
            result["response_type"],

            "response_json":
            json.dumps(
                result,
                default=str
            )
        })