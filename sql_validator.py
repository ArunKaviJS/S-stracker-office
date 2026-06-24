"""
sql_validator.py
----------------
Validates whether a generated SQL string is structurally complete
and only references columns that actually exist in each table.

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

# Exact columns per table — used to catch hallucinated column names.
_TABLE_COLUMNS: dict[str, set[str]] = {
    "tbl_battery": {"batteryId","serialNo","warrantyStartDate","warrantyExpiryDate","warrantyDuration","createdOn","modifiedOn","status"},
    "tbl_device": {"deviceId","deviceEndpoint","firmwareVersion","GPSMACAddress","mode","registrationId","registrationDate","fenceId","isOutOfFence","warrantyStartDate","warrantyExpiryDate","warrantyDuration","lastUpdated","status","lastAddress"},
    "tbl_device_claim_history": {"deviceClaimId","deviceId","warrentyType","doneBy","claimNotes","resolveNotes","resolvedDate","createdOn","status"},
    "tbl_device_data": {"deviceDataId","trolleyId","deviceEndpoint","firmwareVersion","momentDetection","timestamp","status","intervalTimeset","GPSLatitude","GPSLongitude","address","locationSource","OtaTrigger","batteryLevel","batteryFault"},
    "tbl_device_history": {"historyId","deviceEndpoint","latitude","longitude","trolleyId","geozoneId","geolayerId","createdOn","modifiedOn","status","nestId","locationSource","address"},
    "tbl_geolayers": {"geolayerId","geolayerName","buildingName","floorNo","createdOn","modifiedOn","status","boundaryColor"},
    "tbl_geozones": {"geozoneId","geozoneName","tag","tagId","geolayerId","boundaryColor","createdOn","modifiedOn","status","type","noOfTrolleys"},
    "tbl_nest": {"nestId","nestName","geozoneId","geolayerId","minTrolleyLimit","boundaryColor","createdOn","modifiedOn","status","availableTrolly"},
    "tbl_trolley": {"trolleyId","trolleyName","serialNo","deviceId","createdOn","modifiedOn","status","type","maintenanceStatus","lastCleaned","latestHistoryId","latestLatitude","latestLongitude","latestGeozoneId","latestGeolayerId","latestNestId","latestLocationSource","latestAddress","latestHistoryTime","latestDeviceDataId","latestBatteryLevel","latestDataTimestamp","latestIntervalTimeset"},
    "tbl_trolley_maintanence": {"maintenanceId","type","reason","completedNotes","doneBy","image1","image2","createdOn","modifiedOn","status","trolleyId"},
    "tbl_alerts": {"alertId","alertName","key","trolleyId","createdOn","modifiedOn","status","recentGeozoneId","assigneeId"},
    "tbl_alerts_history": {"historyId","alertId","title","notes","doneBy","createdOn","status","id","type"},
    "tbl_duty_roaster": {"rosterId","shift","totalPushers","totalWorkers","createdOn","modifiedOn","status","shiftDate"},
}

# Aliases that SQL lets you use in place of the real column (none currently).
_AGGREGATE_FUNCS = re.compile(r"(?i)\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|IFNULL|IF|CASE|CAST|CONVERT|DATE|YEAR|MONTH|DAY|NOW|DATEDIFF|TIMESTAMPDIFF|LAG|LEAD|ROW_NUMBER|RANK|DENSE_RANK|GROUP_CONCAT|NULLIF|ISNULL)\b")


def _extract_table_aliases(sql: str) -> dict[str, str]:
    """Return {alias: table_name} from FROM/JOIN clauses."""
    aliases: dict[str, str] = {}
    pattern = re.compile(
        r"(?i)(?:FROM|JOIN)\s+(\w+)\s+(?:AS\s+)?(\w+)",
    )
    for m in pattern.finditer(sql):
        tbl, alias = m.group(1).lower(), m.group(2).lower()
        aliases[alias] = tbl
        aliases[tbl] = tbl  # table name maps to itself too
    # Also register bare table names without alias
    bare = re.compile(r"(?i)(?:FROM|JOIN)\s+(\w+)(?:\s+(?:WHERE|JOIN|ON|GROUP|ORDER|LIMIT|HAVING|LEFT|RIGHT|INNER|OUTER|$))?")
    for m in bare.finditer(sql):
        tbl = m.group(1).lower()
        if tbl not in aliases:
            aliases[tbl] = tbl
    return aliases


def validate_columns(sql: str) -> tuple[bool, str]:
    """
    Check that every `alias.column` reference in the SQL maps to a real column
    in the aliased table.  Returns (True, "") on pass or (False, reason) on fail.
    """
    aliases = _extract_table_aliases(sql)

    # Match patterns like  t.trolleyName  or  tbl_trolley_maintanence.trolleyName
    col_ref = re.compile(r"\b(\w+)\.(\w+)\b")
    for m in col_ref.finditer(sql):
        prefix, col = m.group(1).lower(), m.group(2)
        table = aliases.get(prefix)
        if table is None:
            continue  # unknown alias — skip, can't validate
        known = _TABLE_COLUMNS.get(table)
        if known is None:
            continue  # table not in our schema map — skip
        if col.lower() not in {c.lower() for c in known}:
            # Ignore if it looks like a computed alias reference
            if not _AGGREGATE_FUNCS.match(col):
                return False, f"Column '{col}' does not exist in '{table}'"

    return True, ""


def is_complete_sql(sql: str) -> bool:
    """
    Return True when sql looks like a structurally complete MySQL SELECT
    that only references columns that actually exist in each table.
    Returns False for empty strings, bare keywords, truncated clauses,
    or hallucinated column names.
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

    ok, reason = validate_columns(stripped)
    if not ok:
        print(f"[sql_validator] Column validation failed: {reason}")
        return False

    return True