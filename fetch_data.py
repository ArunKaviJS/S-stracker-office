import pandas as pd

from sqlalchemy import text

# ============================================================
# FETCH NEW DATA FROM DB1
# STORE INTO DB2
# ============================================================

def fetch_and_copy_data(
    source_engine,
    dest_engine
):

    # ========================================================
    # CREATE TRACKER TABLE
    # ========================================================

    create_tracker_query = """
    CREATE TABLE IF NOT EXISTS sync_tracker (
        process_name VARCHAR(100) PRIMARY KEY,
        last_processed_id BIGINT
    )
    """

    
    with dest_engine.begin() as conn:
        conn.execute(text(create_tracker_query))

    # ========================================================
    # INSERT INITIAL VALUE
    # ========================================================

    insert_initial_query = """
    INSERT IGNORE INTO sync_tracker (
        process_name,
        last_processed_id
    )
    VALUES (
        'tbl_device_history_sync',
        0
    )
    """

    with dest_engine.begin() as conn:
        conn.execute(text(insert_initial_query))

    # ========================================================
    # GET LAST PROCESSED ID
    # ========================================================

    last_id_query = """
    SELECT last_processed_id
    FROM sync_tracker
    WHERE process_name = 'tbl_device_history_sync'
    """

    last_processed_id = pd.read_sql(
        last_id_query,
        dest_engine
    ).iloc[0]["last_processed_id"]

    print(f"Last Processed ID : {last_processed_id}")

    # ========================================================
    # FETCH ONLY NEW DATA
    # ========================================================

    fetch_query = f"""
        SELECT
            historyId,
            trolleyId,
            geozoneId,
            createdOn,
            status
        FROM tbl_device_history
        WHERE historyId > {last_processed_id}
        ORDER BY historyId ASC
        """

    new_data = pd.read_sql(
        fetch_query,
        source_engine
    )

    # ========================================================
    # NO NEW DATA
    # ========================================================

    if new_data.empty:

        print("No New Data Found")

        return False

    print(f"New Rows Found : {len(new_data)}")

    # ========================================================
    # STORE INTO DB2
    # ========================================================

    new_data.to_sql(
        "tbl_device_history_copy",
        dest_engine,
        if_exists="append",
        index=False
    )

    print("New Data Stored into DB2")

    # ========================================================
    # UPDATE TRACKER
    # ========================================================

    new_last_id = int(
        new_data["historyId"].max()
    )

    update_query = f"""
    UPDATE sync_tracker
    SET last_processed_id = {new_last_id}
    WHERE process_name = 'tbl_device_history_sync'
    """

    with dest_engine.begin() as conn:
        conn.execute(text(update_query))

    print("Tracker Updated")

    return True