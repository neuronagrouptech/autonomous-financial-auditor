import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

region = os.getenv("AWS_REGION", "us-east-1")
host = os.getenv("OPENSEARCH_HOST")

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

INDEX_NAME = "audits-vector"

def index_vector(text: str, metadata: dict) -> str:
    doc = {
        "content": text,
        "metadata": metadata
    }
    response = client.index(index=INDEX_NAME, body=doc)
    return response['_id']
