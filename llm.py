import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    BEDROCK_REGION,
    BEDROCK_MODEL_ID
)

from schema_context import SCHEMA_CONTEXT

_bedrock_client = None


def get_bedrock_client():

    global _bedrock_client

    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION
        )

    return _bedrock_client

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


def generate_sql(question):
    """Generate a MySQL query using Claude Sonnet via AWS Bedrock."""
    logger.info('***** Generating SQL via Claude Sonnet AWS Bedrock *****')

    bedrock = get_bedrock_client()

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0,
        "system": (
            "You are a SQL expert. Your ONLY job is to output a single valid MySQL SELECT query. "
            "Rules you must follow strictly:\n"
            "1. Output ONLY the raw SQL query — nothing else.\n"
            "2. No explanations, no comments, no markdown, no backticks, no code fences.\n"
            "3. Never use DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, or any destructive statement.\n"
            "4. The query must start directly with SELECT.\n"
            f"\n{SCHEMA_CONTEXT}"
        ),
        "messages": [
            {
                "role": "user",
                "content": f"Write a MySQL query for: {question}"
            }
        ]
    })

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=body
    )

    result = json.loads(response["body"].read())

    sql = result["content"][0]["text"].strip()

    sql = (
        sql
        .replace("```sql", "")
        .replace("```", "")
        .strip()
    )

    logger.info("Generated SQL (Claude):", sql)

    return sql


def detect_intent(question):
    """Classify question into single_line, table, or summary."""
    logger.info('******** caling detecting intent********')
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
    logger.info('**** calling single_line llm for answer****')
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
    logger.info(response.choices[0].message.content.strip())
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
    logger.info('******* calling summary llm *******')
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
