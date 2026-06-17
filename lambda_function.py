"""
KPI Insights — Trends rollup Lambda.

Reads the operational (main) DB and writes the rollup tables in the AI DB
(`tbl_kpi_daily`, `tbl_kpi_weekly`) that back the Operational Trends page.

The Operations Overview page is computed LIVE by the API and is NOT handled here.
Per-KPI logic and SQL: ../docs/kpi-lambda-spec.md

Runtime:  Python 3.12 with a layer that provides `pymysql`.
Env vars: DB_HOST / DB_USERNAME / DB_PASSWORD / DB_DATABASE        (main DB)
          AI_DB_HOST / AI_DB_USERNAME / AI_DB_PASSWORD / AI_DB_DATABASE (AI DB)
Event:    {} runs for yesterday; {"date": "YYYY-MM-DD"} for a specific day/backfill.
"""
import os
import ssl
import datetime as dt
import pymysql

# ── Constants (match the API and docs/kpi-lambda-spec.md) ────────────────────
ALERT_OOZ = "TROLLEY OUT OF ZONE"
ALERT_BATTERY = "BATTERY ALERT"
ALERT_SCATTERED = "SCATTERED TROLLEY"
STATUS_RESOLVED = "0"
ACTIVE = "1"


def _round(v, dp=2):
    return None if v is None else round(float(v), dp)


# ── Connections ──────────────────────────────────────────────────────────────
def main_conn():
    # Operational DB — no SSL (matches the API config).
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        db=os.environ["DB_DATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def ai_conn():
    # AI DB on RDS — SSL on, no cert verification (matches rejectUnauthorized:false).
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return pymysql.connect(
        host=os.environ["AI_DB_HOST"],
        user=os.environ["AI_DB_USERNAME"],
        password=os.environ["AI_DB_PASSWORD"],
        db=os.environ["AI_DB_DATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        ssl=ctx,
    )


# ── Shared helpers ───────────────────────────────────────────────────────────
def active_trolley_count(main) -> int:
    with main.cursor() as c:
        c.execute("SELECT COUNT(*) AS n FROM tbl_trolley WHERE status=%s", (ACTIVE,))
        return int(c.fetchone()["n"])


# A device_history row is a transition when its geozone differs from the same
# trolley's previous row, within [day, next_day).
_TRANSITIONS = """
  SELECT trolleyId FROM (
    SELECT trolleyId, geozoneId,
           LAG(geozoneId) OVER (PARTITION BY trolleyId ORDER BY historyId) AS prev_geozone
    FROM tbl_device_history
    WHERE createdOn >= %s AND createdOn < %s AND geozoneId > 0
  ) h
  WHERE prev_geozone IS NOT NULL AND prev_geozone <> geozoneId
"""


# ── KPI 1: fleet_utilisation_rate (daily) ────────────────────────────────────
def fleet_utilisation_rate(main, day, next_day, active):
    """Distinct trolleys with >=1 geozone transition that day / active trolleys * 100."""
    with main.cursor() as c:
        c.execute(f"SELECT COUNT(DISTINCT trolleyId) AS n FROM ({_TRANSITIONS}) t",
                  (day, next_day))
        utilised = int(c.fetchone()["n"])
    return _round(utilised / active * 100) if active else 0.0


# ── KPI 2: per-type alert counts (daily) ─────────────────────────────────────
def daily_alert_counts(main, day) -> dict:
    """COUNT of alerts grouped by type for the day."""
    with main.cursor() as c:
        c.execute(
            "SELECT alertName, COUNT(*) AS cnt FROM tbl_alerts "
            "WHERE DATE(createdOn)=%s GROUP BY alertName", (day,))
        m = {r["alertName"]: int(r["cnt"]) for r in c.fetchall()}
    return {
        "ooz": m.get(ALERT_OOZ, 0),
        "battery": m.get(ALERT_BATTERY, 0),
        "scattered": m.get(ALERT_SCATTERED, 0),
    }


# ── KPI 3: MTTR — overall + per type (daily) ─────────────────────────────────
def daily_mttr(main, day) -> dict:
    """Avg minutes between createdOn and modifiedOn for resolved alerts."""
    with main.cursor() as c:
        c.execute(
            "SELECT alertName, AVG(CASE WHEN status=%s "
            "  THEN TIMESTAMPDIFF(MINUTE, createdOn, modifiedOn) END) AS mttr "
            "FROM tbl_alerts WHERE DATE(createdOn)=%s GROUP BY alertName",
            (STATUS_RESOLVED, day))
        per = {r["alertName"]: r["mttr"] for r in c.fetchall()}
        c.execute(
            "SELECT AVG(TIMESTAMPDIFF(MINUTE, createdOn, modifiedOn)) AS mttr "
            "FROM tbl_alerts WHERE status=%s AND DATE(createdOn)=%s",
            (STATUS_RESOLVED, day))
        overall = c.fetchone()["mttr"]
    return {
        "overall": _round(overall),
        "ooz": _round(per.get(ALERT_OOZ)),
        "battery": _round(per.get(ALERT_BATTERY)),
        "scattered": _round(per.get(ALERT_SCATTERED)),
    }


# ── Write: tbl_kpi_daily (upsert) ────────────────────────────────────────────
def upsert_daily(ai, day, util, mttr, counts):
    with ai.cursor() as c:
        c.execute(
            """INSERT INTO tbl_kpi_daily
                 (kpi_date, fleet_utilisation_rate, fleet_mttr_min,
                  mttr_ooz_min, mttr_battery_min, mttr_scattered_min,
                  alert_count_ooz, alert_count_battery, alert_count_scattered)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 fleet_utilisation_rate=VALUES(fleet_utilisation_rate),
                 fleet_mttr_min=VALUES(fleet_mttr_min),
                 mttr_ooz_min=VALUES(mttr_ooz_min),
                 mttr_battery_min=VALUES(mttr_battery_min),
                 mttr_scattered_min=VALUES(mttr_scattered_min),
                 alert_count_ooz=VALUES(alert_count_ooz),
                 alert_count_battery=VALUES(alert_count_battery),
                 alert_count_scattered=VALUES(alert_count_scattered)""",
            (day, util, mttr["overall"], mttr["ooz"], mttr["battery"], mttr["scattered"],
             counts["ooz"], counts["battery"], counts["scattered"]))


# ── KPI 4: weekly rollup (Utilisation / MTTR / Alert-Volume trends) ──────────
def rollup_weekly(ai, day):
    """Roll the daily rows of the day's ISO week up into tbl_kpi_weekly."""
    with ai.cursor() as c:
        c.execute(
            """INSERT INTO tbl_kpi_weekly
                 (year_week, week_start, utilisation_rate,
                  mttr_ooz, mttr_battery, mttr_scattered,
                  alert_ooz, alert_battery, alert_scattered)
               SELECT YEARWEEK(kpi_date,3), MIN(kpi_date),
                      AVG(fleet_utilisation_rate),
                      AVG(mttr_ooz_min), AVG(mttr_battery_min), AVG(mttr_scattered_min),
                      SUM(alert_count_ooz), SUM(alert_count_battery), SUM(alert_count_scattered)
               FROM tbl_kpi_daily
               WHERE YEARWEEK(kpi_date,3) = YEARWEEK(%s,3)
               GROUP BY YEARWEEK(kpi_date,3)
               ON DUPLICATE KEY UPDATE
                 week_start=VALUES(week_start),
                 utilisation_rate=VALUES(utilisation_rate),
                 mttr_ooz=VALUES(mttr_ooz), mttr_battery=VALUES(mttr_battery),
                 mttr_scattered=VALUES(mttr_scattered),
                 alert_ooz=VALUES(alert_ooz), alert_battery=VALUES(alert_battery),
                 alert_scattered=VALUES(alert_scattered)""",
            (day,))


# ── Handler ──────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    # Process yesterday by default, or event["date"] = "YYYY-MM-DD" for backfill.
    day = (event or {}).get("date")
    if not day:
        day = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    next_day = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()

    main, ai = main_conn(), ai_conn()
    try:
        active = active_trolley_count(main)
        util = fleet_utilisation_rate(main, day, next_day, active)
        counts = daily_alert_counts(main, day)
        mttr = daily_mttr(main, day)
        upsert_daily(ai, day, util, mttr, counts)   # tbl_kpi_daily
        rollup_weekly(ai, day)                       # tbl_kpi_weekly
        
        return {
            "statusCode": 200,
            "body": {
                "date": day,
                "utilisation": util,
                "alerts": counts,
                "mttr": mttr
            }
        }
        
    except Exception as e:
         return {
            "statusCode": 500,
            "body": str(e)
        }
        
    finally:
        main.close()
        ai.close()


