BLOCKED_WORDS = [
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "INSERT",
    "UPDATE"
]


class BlockedQueryError(Exception):
    pass


def check_question(question):
    """Raise BlockedQueryError if the question itself asks for a blocked operation."""
    print("checking user question")
    q_upper = question.upper()
    for word in BLOCKED_WORDS:
        if word in q_upper:
            print('restricted words',word)
            raise BlockedQueryError(word)


def validate_sql(sql, user_id=None, question=None):
    print('validating sql')
    sql_upper = sql.upper()

    for word in BLOCKED_WORDS:
        if word in sql_upper:
            print('restrict for sql', word)
            _save_blocked(user_id, question, sql)
            raise BlockedQueryError(word)

    if not sql_upper.startswith("SELECT"):
        _save_blocked(user_id, question, sql)
        raise BlockedQueryError("NOT_SELECT")


def _save_blocked(user_id, question, sql):
    """Persist the blocked query attempt to DB."""
    try:
        from response_store import save_response
        save_response(
            user_id=user_id,
            question=question,
            sql_query=sql,
            intent="sql_error",
            chat_title="I have no permission to execute database operations that modify data or schema, including DROP, DELETE, ALTER, TRUNCATE, INSERT, and UPDATE.",
            response=None
        )
    except Exception as db_err:
        print("Failed to save blocked query:", db_err)
