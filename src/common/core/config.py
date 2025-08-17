"""Centralized Env Variable Retriever"""
import os
from dotenv import load_dotenv


if os.getenv("ENV", "local") == "local":
    from dotenv import load_dotenv
    load_dotenv()

# AWS Variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "amazon.nova-lite-v1:0")
EMBED_MODEL_ID = os.getenv("EMBED_MODEL_ID")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
LOCAL_PROFILE_NAME=os.getenv("LOCAL_PROFILE_NAME")

## Target GIT
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
S3_BUCKET_NAME= os.getenv("S3_BUCKET_NAME")
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID")


