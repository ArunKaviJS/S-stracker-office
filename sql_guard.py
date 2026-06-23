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
    q_upper = question.upper()
    for word in BLOCKED_WORDS:
        if word in q_upper:
            raise BlockedQueryError(word)


def validate_sql(sql):

    sql_upper = sql.upper()

    for word in BLOCKED_WORDS:
        if word in sql_upper:
            raise BlockedQueryError(word)

    if not sql_upper.startswith("SELECT"):
        raise BlockedQueryError("NOT_SELECT")
