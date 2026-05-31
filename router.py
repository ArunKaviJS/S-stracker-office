from s3_utils import upload_dataframe_to_s3
import json

SMALL_ROWS = 10
SMALL_COLS = 4


def generate_table_summary(
        client,
        deployment,
        question,
        df
):

    sample = df.head(20).to_string(index=False)

    response = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content":
                """
                You are a data analyst.

                Return ONLY valid JSON.

                {
                  "title": "...",
                  "summary": "..."
                }

                title:
                Short dashboard-style heading.

                summary:
                One or two sentences.
                """
            },
            {
                "role": "user",
                "content":
                f"""
                Question:
                {question}

                Sample Data:
                {sample}
                """
            }
        ]
    )

    return json.loads(
        response.choices[0]
        .message.content
    )

def narrate(client, deployment, question, df):

    txt = df.to_string(index=False)

    response = client.chat.completions.create(
        model=deployment,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a trolley management assistant. "
                    "Answer in 1-3 sentences."
                )
            },
            {
                "role": "user",
                "content":
                f"Question: {question}\n\n"
                f"Database Result:\n{txt}"
            }
        ]
    )

    return response.choices[0].message.content


def route(question, df, client, deployment):

    rows, cols = df.shape

    if rows == 0:

        return {
            "response_type": "text",
            "message": "No data found.",
            "row_count": 0,
            "columns": [],
            "data": []
        }

    small_result = (
        rows <= SMALL_ROWS and
        cols <= SMALL_COLS
    )

    if small_result:

        answer = narrate(
            client,
            deployment,
            question,
            df
        )

        return {
            "response_type": "text",
            "message": answer,
            "row_count": rows,
            "columns": list(df.columns),
            "data": df.to_dict("records")
        }

    table_info = generate_table_summary(
    client,
    deployment,
    question,
    df
    )

    csv_url = upload_dataframe_to_s3(df)
    
    return {

        "response_type": "table",
        
        "title":
        table_info["title"],

        "summary":
        table_info["summary"],

        "message":
        f"Found {rows} records.",

        "row_count":
        rows,

        "columns":
        list(df.columns),

        "data":
        df.to_dict("records"),
        
        "csv_url":
        csv_url
    }