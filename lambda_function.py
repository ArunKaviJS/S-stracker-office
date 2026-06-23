import json

from main import run


def lambda_handler(event, context):

    try:

        body = event

        if "body" in event:
            body = json.loads(event["body"])

        question = body.get("question", "")
        user_id  = body.get("userId", "")

        result = run(question, user_id)

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str,indent=10)
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "body": json.dumps({
                "intent": "error",
                "message": str(e)
            })
        }
