import boto3
import json
import os

client = boto3.client('bedrock-runtime', region_name=os.getenv("AWS_REGION", "us-east-1"))

def call_bedrock_llm(prompt: str) -> str:
    response = client.invoke_model(
        modelId='amazon.titan-llm',  # Ajusta al modelo Bedrock disponible
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "prompt": prompt,
            "maxTokens": 500,
            "temperature": 0.7
        })
    )
    body = json.loads(response['body'].read())
    return body['completions'][0]['data']['text']
