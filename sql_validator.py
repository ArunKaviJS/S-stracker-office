"""
sql_validator.py
----------------
Validates whether a generated SQL string is structurally complete.

Public API
----------
    is_complete_sql(sql: str) -> bool
"""

import re

# Each pattern matches a SQL string that is clearly truncated/incomplete.
# Use \b word boundaries carefully — avoid false matches on column names
# that end with SQL keywords (e.g. createdOn, modifiedOn).
_INCOMPLETE_PATTERNS = [
    r"(?i)^\s*SELECT\s*;?\s*$",            # bare SELECT
    r"(?i)^\s*SELECT\s+\*\s*;?\s*$",       # SELECT *
    r"(?i)^\s*SELECT\s+\*\s+FROM\s*;?\s*$",# SELECT * FROM
    r"(?i)\bFROM\s*;?\s*$",                # ends after FROM
    r"(?i)\bWHERE\s*;?\s*$",               # ends after WHERE
    r"(?i)\bAND\s*;?\s*$",                 # ends after AND
    r"(?i)(?<!\w)OR\s*;?\s*$",             # ends after OR (not part of a word like createdOn)
    r"(?i)\bJOIN\s*;?\s*$",                # ends after JOIN
    r"(?i)(?<!\w)ON\s*;?\s*$",             # ends after ON (not creat-ed-ON / modifi-ed-ON)
    r"(?i)\bHAVING\s*;?\s*$",              # ends after HAVING
    r"(?i)\bGROUP\s+BY\s*;?\s*$",          # ends after GROUP BY
    r"(?i)\bORDER\s+BY\s*;?\s*$",          # ends after ORDER BY
    r"(?i)\bLIMIT\s*;?\s*$",               # ends after LIMIT
    r"(?i)\bIN\s*\(\s*;?\s*$",             # ends with IN (  — open paren, nothing after
    r"(?i)\bIN\s*\(\s*\)\s*;?\s*$",        # ends with IN () — empty list, always invalid
    r"(?i)[=]\s*;?\s*$",                   # ends after =
    r"(?i)[><]=?\s*;?\s*$",                # ends after < > <= >=
    r"(?i)!=\s*;?\s*$",                    # ends after !=
    r"(?i)<>\s*;?\s*$",                    # ends after <>
]

# A valid SELECT must have at least: SELECT <something> FROM <word>
_VALID_SELECT_RE = re.compile(
    r"(?i)^\s*SELECT\s+.+\s+FROM\s+[\w`\[\]\"]+",
    re.DOTALL,
)


def is_complete_sql(sql: str) -> bool:
    """
    Return True when sql looks like a structurally complete MySQL SELECT.
    Returns False for empty strings, bare keywords, or truncated clauses.
    """
    if not sql or not sql.strip():
        return False

    stripped = sql.strip()

    # Non-SELECT statements (SHOW, DESCRIBE, etc.) — treat as complete
    if not re.match(r"(?i)^\s*SELECT\b", stripped):
        return bool(stripped)

    for pattern in _INCOMPLETE_PATTERNS:
        if re.search(pattern, stripped):
            return False

    if not _VALID_SELECT_RE.search(stripped):
        return False

    return True
