import math

from llm import narrate, generate_summary
from s3_utils import upload_dataframe_to_s3_xlsx

PAGE_SIZE = 10
S3_THRESHOLD = 50


def _paginate(df):
    print("Split df into pages of PAGE_SIZE rows, returned as a dict.")
    records = df.to_dict("records")
    total_pages = math.ceil(len(records) / PAGE_SIZE)
    pages = {}
    for i in range(total_pages):
        start = i * PAGE_SIZE
        pages[f"page_{i + 1}"] = records[start: start + PAGE_SIZE]
    return pages


def route(question, intent, df):
    """
    Build the response dict using the pre-detected intent:
      {
        "intent": str,
        "chatTitle": str,
        "response": None | dict | str
      }
    """
    print('Build the response dict using the pre-detected intent ,df')
    rows, _ = df.shape

    # Fallback: no data returned by query
    if rows == 0:
        print(' no data found')
        return {
            "intent": "no_data",
            "chatTitle": "No data found for this query",
            "response": None
        }

    # --- single_line intent ---
    if intent == "single_line":
        print('single line intent')
        answer = narrate(question, df)
        return {
            "intent": "single_line",
            "chatTitle": answer,
            "response": None
        }

    # --- summary intent ---
    if intent == "summary":
    
        summary_data = generate_summary(question, df.to_string(index=False))
        print('generated summary data',summary_data)
        chat_title = summary_data.pop("chatTitle", question)
        print('chat title',chat_title)
        return {
            "intent": "summary",
            "chatTitle": chat_title,
            "response": summary_data
        }

    # --- table intent ---
    chat_title = f"{rows} results found in your query"

    if rows <= PAGE_SIZE:
        print('small table')
        return {
            "intent": "small_table",
            "chatTitle": chat_title,
            "response": df.to_dict("records")
        }

    if rows <= S3_THRESHOLD:
        print('large table')
        return {
            "intent": "large_table",
            "chatTitle": chat_title,
            "response": _paginate(df)
        }

    # >50 rows: upload as XLSX to S3
    xlsx_url = upload_dataframe_to_s3_xlsx(df)
    return {
        "intent": "S3_URL",
        "chatTitle": chat_title,
        "response": xlsx_url
    }
