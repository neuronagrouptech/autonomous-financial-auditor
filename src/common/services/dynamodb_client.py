import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name=os.getenv("AWS_REGION", "us-east-1"))
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE"))

def save_audit_metadata(data: dict):
    item = {
        "audit_id": str(datetime.utcnow().timestamp()),
        "repo": data["repo"],
        "branch": data["branch"],
        "result": data["result"],
        "vector_id": data["vector_id"],
        "timestamp": int(datetime.utcnow().timestamp())
    }
    table.put_item(Item=item)
