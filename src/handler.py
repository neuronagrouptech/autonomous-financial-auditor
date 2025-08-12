import os
import json
from agent import run_audit

def lambda_handler(event, context):
    repo = os.environ['GITHUB_REPO']
    branch = os.environ.get('GITHUB_BRANCH', 'main')
    github_token = os.environ['GITHUB_TOKEN']

    result = run_audit(repo, branch, github_token, context)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Audit completed", "details": result})
    }

if __name__ == "__main__":
    import dotenv, sys
    dotenv.load_dotenv()
    run_audit(
        os.getenv("GITHUB_REPO"),
        os.getenv("GITHUB_BRANCH", "main"),
        os.getenv("GITHUB_TOKEN"),
        context=None
    )
