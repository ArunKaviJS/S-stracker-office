import re

# SQL keywords that modify or alter database data/schema.
# Checked with word-boundary matching so column names like
# UPDATED_AT, DELETED_FLAG, CREATED_BY are never false-positives.
BLOCKED_WORDS = [
    # DML
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "MERGE",
    "UPSERT",
    # DDL
    "CREATE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "RENAME",
    # DCL
    "GRANT",
    "REVOKE",
    # Proc / admin
    "CALL",
    "EXEC",
    "EXECUTE",
    "LOAD",
    "IMPORT",
]

# Pre-compile one pattern per blocked word for fast, exact-word matching.
_BLOCKED_PATTERNS = {
    word: re.compile(rf"(?i)\b{word}\b")
    for word in BLOCKED_WORDS
}


class BlockedQueryError(Exception):
    pass


def check_question(question: str) -> None:
    """Raise BlockedQueryError if the user's question asks for a blocked operation."""
    print("checking user question")
    for word, pattern in _BLOCKED_PATTERNS.items():
        if pattern.search(question):
            print("restricted word in question:", word)
            raise BlockedQueryError(word)


def validate_sql(sql: str, user_id=None, question: str = None) -> None:
    """Raise BlockedQueryError if the generated SQL contains any data-altering keyword."""
    print("validating sql")

    if not sql or not sql.strip():
        _save_blocked(user_id, question, sql)
        raise BlockedQueryError("EMPTY_SQL")

    if not re.match(r"(?i)^\s*SELECT\b", sql.strip()):
        _save_blocked(user_id, question, sql)
        raise BlockedQueryError("NOT_SELECT")

    for word, pattern in _BLOCKED_PATTERNS.items():
        if pattern.search(sql):
            print("restricted word in sql:", word)
            _save_blocked(user_id, question, sql)
            raise BlockedQueryError(word)


def _save_blocked(user_id, question, sql):
    """Persist the blocked query attempt to the DB."""
    try:
        from response_store import save_response
        save_response(
            user_id=user_id,
            question=question,
            sql_query=sql,
            intent="sql_error",
            chat_title=(
                "I have no permission to execute database operations that "
                "modify data or schema."
            ),
            response=None,
        )
    except Exception as db_err:
        print("Failed to save blocked query:", db_err)
