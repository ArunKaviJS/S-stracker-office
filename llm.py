import json

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT
)

from schema_context import SCHEMA_CONTEXT
from sql_validator import is_complete_sql      # <-- new import


_client = None


def get_client():

    global _client

    if _client is None:

        _client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )

    return _client



def _call_llm_for_sql(client, question):
    """Single LLM call that returns a stripped SQL string."""
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
        messages=[
            {"role": "system", "content": SCHEMA_CONTEXT},
            {"role": "user",   "content": f"Write a MySQL query for: {question}"}
        ]
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql

def generate_sql(question, max_retries=2):
    """
    Generate a MySQL query for the given question.
 
    After each LLM call the SQL is validated with is_complete_sql().
    If incomplete, generate_sql is retried up to max_retries times.
    Raises RuntimeError if still incomplete after all attempts.
    """
    print('***** Generating SQL *****')
    client = get_client()
 
    for attempt in range(1, max_retries + 1):
        sql = _call_llm_for_sql(client, question)
        print(f'[generate_sql] Attempt {attempt} SQL: {sql}')
 
        if is_complete_sql(sql):
            print('[generate_sql] SQL validated OK.')
            return sql
 
        print(f'[generate_sql] SQL incomplete on attempt {attempt}, retrying …')
 
    raise RuntimeError(
        f"generate_sql failed to produce a complete SQL after {max_retries} attempts.\n"
        f"Last SQL: {sql}"
    )


def detect_intent(question):
    """Classify question into single_line, table, or summary."""
    print('******** caling detecting intent********')
    client = get_client()

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify the user's question into exactly one intent:\n"
                    "- single_line: expects a single value or very short factual answer "
                    "(e.g. 'which trolley is most idle?', 'what is the total count?')\n"
                    "- table: expects a list or tabular data "
                    "(e.g. 'show all idle trolleys', 'list trolleys idle for more than 10 hours')\n"
                    "- summary: expects a narrative analysis, report, or summary "
                    "(e.g. 'show me the alert summary for this week', 'give me a weekly report')\n\n"
                    "Return ONLY one word: single_line, table, or summary"
                )
            },
            {"role": "user", "content": question}
        ]
    )

    intent = response.choices[0].message.content.strip().lower()

    if intent not in ("single_line", "table", "summary"):
        intent = "table"

    return intent


def narrate(client, deployment, question, df):
    """Single LLM call: 1-3 sentence answer for single_line intent."""
    print('**** calling single_line llm for answer****')
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
                "content": f"Question: {question}\n\nDatabase Result:\n{txt}"
            }
        ]
    )
    print(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()


def generate_summary(question, df_text):
    """
    Single LLM call for summary intent.

    Returns a dict:
      {
        "chatTitle": "<short dashboard title>",
        "intro": "<one sentence headline>",
        "sections": [
          {"icon": "...", "title": "...", "type": "paragraph|bullets|numbered", "items": [...]}
        ]
      }
    """
    print('******* calling summary llm *******')
    client = get_client()

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a logistics data analyst. "
                    "Analyse the data and return ONLY valid JSON matching this schema "
                    "(no markdown fences):\n\n"
                    "{\n"
                    '  "chatTitle": "<short dashboard-style title, max 8 words>",\n'
                    '  "intro": "<one sentence headline insight>",\n'
                    '  "sections": [\n'
                    '    {\n'
                    '      "icon": "<emoji>",\n'
                    '      "title": "<section title>",\n'
                    '      "type": "paragraph | bullets | numbered",\n'
                    '      "items": ["<line1>", "<line2>"]\n'
                    "    }\n"
                    "  ]\n"
                    "}\n\n"
                    "Always include:\n"
                    "  - A 📖 Details section (type: paragraph, single item)\n"
                    "  - A key insights section with an appropriate icon (type: bullets)\n"
                    "  - A recommended actions section with an appropriate icon (type: numbered)\n"
                    "  - An expected benefits section with an appropriate icon (type: bullets)\n"
                    "Section titles and icons should match the context of the question."
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nData:\n{df_text}"
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    
    return json.loads(raw)
