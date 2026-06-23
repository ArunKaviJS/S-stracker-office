"""
sql_validator.py
----------------
Validates whether a generated SQL string is structurally complete.

Public API
----------
    is_complete_sql(sql: str) -> bool
"""

import re

_INCOMPLETE_PATTERNS = [
    r"^\s*SELECT\s*;?\s*$",
    r"^\s*SELECT\s+\*\s*;?\s*$",
    r"^\s*SELECT\s+\*\s+FROM\s*;?\s*$",
    r"(?i)\bFROM\s*;?\s*$",
    r"(?i)\bWHERE\s*;?\s*$",
    r"(?i)\bAND\s*;?\s*$",
    r"(?i)\bOR\s*;?\s*$",
    r"(?i)\bJOIN\s*;?\s*$",
    r"(?i)\bON\s*;?\s*$",
    r"(?i)\bHAVING\s*;?\s*$",
    r"(?i)\bGROUP\s+BY\s*;?\s*$",
    r"(?i)\bORDER\s+BY\s*;?\s*$",
    r"(?i)\bLIMIT\s*;?\s*$",
    r"(?i)\bIN\s*\(\s*\)?\s*;?\s*$",
    r"(?i)=\s*;?\s*$",
    r"(?i)(>|<|>=|<=|!=|<>)\s*;?\s*$",
]

_VALID_SELECT_RE = re.compile(
    r"(?i)^\s*SELECT\s+.+\s+FROM\s+\S+",
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