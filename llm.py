import json

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT
)

from schema_context import SCHEMA_CONTEXT

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


def generate_sql_and_intent(question):
    """
    Single LLM call that returns both the MySQL query and the intent.

    Returns: (sql: str, intent: str)
    intent is one of: single_line | table | summary
    """

    client = get_client()

    system_prompt = (
        SCHEMA_CONTEXT +
        "\n\n"
        "=======================================================================\n"
        "RESPONSE FORMAT\n"
        "=======================================================================\n"
        "Return ONLY valid JSON — no markdown fences, no extra text:\n"
        "{\n"
        '  "sql": "<MySQL query>",\n'
        '  "intent": "<single_line | table | summary>"\n'
        "}\n\n"
        "Intent rules:\n"
        "  single_line – question expects one value or a very short factual answer\n"
        "                (e.g. 'which trolley is most idle?', 'what is the total count?')\n"
        "  table       – question expects a list or tabular data\n"
        "                (e.g. 'show all idle trolleys', 'list trolleys idle for more than 10 hours')\n"
        "  summary     – question expects a narrative analysis, report, or summary\n"
        "                (e.g. 'show me the alert summary for this week', 'give me a weekly report')\n"
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Question: {question}"}
        ]
    )

    raw = response.choices[0].message.content.strip()

    parsed = json.loads(raw)

    sql = (
        parsed["sql"]
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )

    intent = parsed.get("intent", "table").strip().lower()

    if intent not in ("single_line", "table", "summary"):
        intent = "table"

    return sql, intent


def narrate(client, deployment, question, df):
    """Single LLM call: 1-3 sentence answer for single_line intent."""

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

    return response.choices[0].message.content.strip()


def generate_summary(question, df_text):
    """
    Single LLM call for summary intent.

    Returns a dict:
      {
        "chat_title": "<short dashboard title>",
        "intro": "<one sentence headline>",
        "sections": [
          {"icon": "...", "title": "...", "type": "paragraph|bullets|numbered", "items": [...]}
        ]
      }
    """

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
                    '  "chat_title": "<short dashboard-style title, max 8 words>",\n'
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
