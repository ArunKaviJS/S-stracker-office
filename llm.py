import json
import boto3
from config import BEDROCK_MODEL_ID_1, BEDROCK_MODEL_ID_2,AWS_ACCESS_KEY,AWS_SECRET_KEY

from schema_context import SCHEMA_CONTEXT


_bedrock_client = None


def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name="ap-southeast-1",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    # Optional: Only if you're using temporary credentials
    # aws_session_token="YOUR_SESSION_TOKEN"
)
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
    sql = _call_llm_for_sql(question)
    # print(f'[generate_sql] SQL: {sql}')
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
    txt = df.to_string(index=False)
    
    print('****************df and txt for single llm*************')
    print('df',df)
    print('txt',txt)
    print('***********************************************')

    result = _invoke_chat(
        system_prompt=(
            "You are a trolley management assistant. "
            "Below is the data needed to answer the question — treat it as something you already know, "
            "not something you looked up. Do NOT say you lack data or need more information. "
            "Answer the question in 1-5 sentences, in plain, natural, everyday language, "
            "exactly as a helpful human colleague would explain it to someone with no technical background. "

            "STRICT RULES: "
            "1. Never mention or hint at where the information came from — no 'query', 'database', 'data', "
            "'record', 'table', 'system', 'results', 'according to', 'based on', or any similar reference. "
            "2. Never use technical or SQL-related terms — no column names, IDs, status codes, or field names "
            "verbatim; translate them into everyday words (e.g. say 'invited' instead of 'status = invited'). "
            "3. Speak directly and confidently, as if stating a known fact. "
            "4. Do not explain your reasoning or mention that you are interpreting anything — just state the answer. "

            "Example: "
            "Instead of 'Based on the query result, there is 1 user in Invited status' or "
            "'The data shows 1 invited user', say: "
            "'There is 1 user who has been invited but hasn't logged in yet.'"
        ),
        user_content=f"Question: {question}\n\nData (query result):\n{txt}",
        temperature=0,
        max_tokens=512,
    )
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

    raw = _invoke_chat(
        system_prompt = (
            "You are a logistics data analyst. "
            "Analyze the provided data and return ONLY valid JSON matching this schema "
            "(no markdown, no explanations, no code fences):\n\n"

            "{\n"
            '  "chatTitle": "<concise conversational title (8-15 words)>",\n'
            '  "intro": "<one-sentence headline insight>",\n'
            '  "summary": "<one descriptive paragraph summarizing the analysis>",\n'
            '  "findings": [\n'
            '    "<key finding 1>",\n'
            '    "<key finding 2>"\n'
            '  ],\n'
            '  "actions": [\n'
            '    "<recommended action 1>",\n'
            '    "<recommended action 2>"\n'
            '  ],\n'
            '  "impact": [\n'
            '    "<business impact 1>",\n'
            '    "<business impact 2>"\n'
            '  ]\n'
            "}\n\n"

            "Requirements:\n"
            "- Return ONLY valid JSON.\n"
            "- Do NOT include emojis.\n"
            "- Do NOT include presentation fields such as icon, type, or items.\n"
            "- Do NOT include markdown, headings, numbering, or formatting.\n"
            "- Generate concise, business-friendly content.\n"
            "- The summary should be a single paragraph.\n"
            "- Findings should contain key observations from the data.\n"
            "- Actions should contain practical recommendations.\n"
            "- Impact should describe expected operational or business outcomes.\n"
            "- Do not invent data; use only the provided information."
        ),
        user_content=f"Question: {question}\n\nData:\n{df_text}",
        temperature=0,
        max_tokens=2048,
    )

    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
