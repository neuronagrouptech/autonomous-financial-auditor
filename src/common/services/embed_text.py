import json
from botocore.exceptions import ClientError
from src.core.clients import get_bedrock_client
from src.core.config import EMBED_MODEL_ID

def embed_text(text: str):

    client = get_bedrock_client()

    payload = {
        "inputText": text
    }

    try:
        response = client.invoke_model(
            body=json.dumps(payload),
            modelId=EMBED_MODEL_ID,
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response['body'].read())

        return response_body['embedding']
    
    except (ClientError, Exception) as e:
        error = f"ERROR: Can't invoke '{EMBED_MODEL_ID}'. Reason: {e}"
        return error