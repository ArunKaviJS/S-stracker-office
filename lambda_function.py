import os
import pymysql

TABLES = [ "tbl_trolley_maintenance", "tbl_device_history", "tbl_trolley", "tbl_alerts"]

TABLE_ID_COLUMN = {
    "tbl_trolley_maintenance": "maintenanceId",
    "tbl_device_history": "historyId",
    "tbl_trolley": "trolleyId",
    "tbl_alerts" : "alertId"
}


def get_connection(host, user, password, database):
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def get_max_id(conn, table):

    id_col = TABLE_ID_COLUMN[table]

    with conn.cursor() as cur:

        cur.execute(f"""
            SELECT COALESCE(MAX(`{id_col}`), 0) as max_id
            FROM `{table}`
        """)

        return cur.fetchone()["max_id"]


def get_new_rows(conn, table, last_id):

    id_col = TABLE_ID_COLUMN[table]

    with conn.cursor() as cur:

        cur.execute(f"""
            SELECT *
            FROM `{table}`
            WHERE `{id_col}` > %s
            ORDER BY `{id_col}`
        """, (last_id,))

        return cur.fetchall()


def insert_rows(conn, table, rows):

    if not rows:
        return 0

    columns = list(rows[0].keys())

    column_str = ",".join(columns)

    placeholders = ",".join(["%s"] * len(columns))

    sql = f"""
        INSERT INTO {table}
        ({column_str})
        VALUES ({placeholders})
    """

    values = [
        tuple(row[col] for col in columns)
        for row in rows
    ]

    try:

        with conn.cursor() as cur:

            cur.executemany(sql, values)

        conn.commit()

        return len(rows)

    except Exception:

        conn.rollback()

        raise




#==========check table exist======
def table_exists(conn, table):

    with conn.cursor() as cur:

        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = %s
        """, (table,))

        return cur.fetchone()["cnt"] > 0


#=============create table likely in main db if not exist======
def create_table_like(main_conn, ai_conn, table):

    main_db = os.environ["DB_DATABASE"]
    ai_db = os.environ["AI_DB_DATABASE"]

    with ai_conn.cursor() as cur:

        cur.execute(f"""
            CREATE TABLE {ai_db}.{table}
            LIKE {main_db}.{table}
        """)

    ai_conn.commit()

    print(f"Created table {table} in AI_DB")
    
    
def sync_table(main_conn, ai_conn, table):

    print(f"Syncing {table}")

    # Fallback: table missing in AI_DB
    if not table_exists(ai_conn, table):

        print(f"{table} not found in AI_DB")

        create_table_like(
            main_conn,
            ai_conn,
            table
        )

    # Existing flow (unchanged)

    last_ai_id = get_max_id(ai_conn, table)

    print("Last AI id:", last_ai_id)

    rows = get_new_rows(
        main_conn,
        table,
        last_ai_id
    )

    print("Rows to copy:", len(rows))

    inserted = insert_rows(
        ai_conn,
        table,
        rows
    )

    print(f"Inserted {inserted} rows")

def lambda_handler(event, context):

    main_conn = get_connection(
        os.environ["DB_HOST"],
        os.environ["DB_USERNAME"],
        os.environ["DB_PASSWORD"],
        os.environ["DB_DATABASE"]
    )

    ai_conn = get_connection(
        os.environ["AI_DB_HOST"],
        os.environ["AI_DB_USERNAME"],
        os.environ["AI_DB_PASSWORD"],
        os.environ["AI_DB_DATABASE"]
    )

    try:

        for table in TABLES:

            try:
                sync_table(main_conn, ai_conn, table)

            except Exception as e:

                print(f"Error syncing {table}")

                print(e)

        return {
            "statusCode": 200,
            "body": "Sync completed"
        }

    finally:

        main_conn.close()

        ai_conn.close()