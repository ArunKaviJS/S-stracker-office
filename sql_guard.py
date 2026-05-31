def validate_sql(sql):

    sql_upper = sql.upper()

    blocked = [
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "INSERT",
        "UPDATE"
    ]

    for word in blocked:
        if word in sql_upper:
            raise Exception(
                f"Blocked SQL: {word}"
            )

    if not sql_upper.startswith("SELECT"):
        raise Exception(
            "Only SELECT queries allowed"
        )