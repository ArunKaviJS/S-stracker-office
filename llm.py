import json
import boto3

from config import BEDROCK_MODEL_ID_1, BEDROCK_MODEL_ID_2

from schema_context import SCHEMA_CONTEXT


_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(service_name="bedrock-runtime")
    return _bedrock_client


def _call_llm_for_sql(question):
    """Generate SQL using Claude Sonnet on AWS Bedrock."""

    bedrock = get_bedrock_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,   # complex nested queries can exceed 2048 tokens
        "temperature": 0,     # deterministic output, no hallucination drift
        "system": SCHEMA_CONTEXT,
        "messages": [
            {
                "role": "user",
                "content": f"Write a MySQL query for: {question}"
            }
        ]
    }

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID_1,
        body=json.dumps(body)
    )

    result = json.loads(
        response["body"].read().decode("utf-8")
    )

    stop_reason = result.get("stop_reason", "")
    if stop_reason == "max_tokens":
        print("[llm] WARNING: SQL response was truncated (hit max_tokens limit)")

    sql = result["content"][0]["text"].strip()

    # Strip markdown fences if the model wrapped the output
    sql = (
        sql.replace("```sql", "")
           .replace("```mysql", "")
           .replace("```", "")
           .strip()
    )

    return sql


def generate_sql(question):
    """Generate a MySQL query via Claude Sonnet on AWS Bedrock."""
    print('***** Generating SQL via Claude Bedrock *****')
    sql = _call_llm_for_sql(question)
    print(f'[generate_sql] SQL: {sql}')
    return sql


def _invoke_chat(system_prompt, user_content, temperature=0, max_tokens=512):
    """Call Claude on Bedrock via invoke_model for chat functions."""
    bedrock = get_bedrock_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_content}
        ]
    }

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID_2,
        body=json.dumps(body)
    )

    result = json.loads(response["body"].read().decode("utf-8"))
    return result["content"][0]["text"].strip()


def detect_intent(question):
    """Classify question into single_line, table, or summary."""
    print('******** caling detecting intent********')

    intent = _invoke_chat(
        system_prompt=(
            "Classify the user's question into exactly one intent:\n"
            "- single_line: expects a single value or very short factual answer "
            "(e.g. 'which trolley is most idle?', 'what is the total count?')\n"
            "- table: expects a list or tabular data "
            "(e.g. 'show all idle trolleys', 'list trolleys idle for more than 10 hours')\n"
            "- summary: expects a narrative analysis, report, or summary "
            "(e.g. 'show me the alert summary for this week', 'give me a weekly report')\n\n"
            "Return ONLY one word: single_line, table, or summary"
        ),
        user_content=question,
        temperature=0,
    )

    intent = intent.lower()
    if intent not in ("single_line", "table", "summary"):
        intent = "table"

    return intent


def narrate(question, df):
    """Single LLM call: 1-3 sentence answer for single_line intent."""
    print('**** calling single_line llm for answer****')
    txt = df.to_string(index=False)

    result = _invoke_chat(
        system_prompt=(
            "You are a trolley management assistant. "
            "Answer in 1-3 sentences directly from the data provided. "
            "Never mention the database, query results, data source, or any backend process. "
            "Never start with phrases like 'Based on the data', 'According to the results', "
            "'The database shows', 'From the records', or similar. "
            "Speak naturally as if you already know the answer."
        ),
        user_content=f"Question: {question}\n\nData:\n{txt}",
        temperature=0,
        max_tokens=512,
    )
    print(result)
    return result


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

    raw = _invoke_chat(
        system_prompt=(
            "You are a logistics data analyst. "
            "Analyse the data and return ONLY valid JSON matching this schema "
            "(no markdown fences):\n\n"
            "{\n"
            ' "chatTitle": "<concise conversational title summarizing the analysis in 8-15 words, suitable for display in 1-2 UI lines>",\n'
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
            "Requirements:\n"
            "- Generate section titles dynamically based on the content and business context.\n"
            "- Do NOT use fixed titles such as 'Details', 'Key Insights', "
            "'Recommended Actions', or 'Expected Benefits' unless they are naturally appropriate.\n"
            "- Include exactly one descriptive summary section (type: paragraph).\n"
            "- Include at least one insights/findings section (type: bullets).\n"
            "- Include one action-oriented section (type: numbered).\n"
            "- Include one impact/benefits/outcomes section (type: bullets).\n"
            "- Choose relevant emojis and section titles that match the question and analysis.\n"
            "- Keep titles concise, dashboard-style, and business-friendly.\n"
        ),
        user_content=f"Question: {question}\n\nData:\n{df_text}",
        temperature=0,
        max_tokens=2048,
    )

    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
