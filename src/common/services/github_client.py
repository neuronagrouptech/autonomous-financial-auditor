import requests
from datetime import datetime
import uuid
import base64
from typing import Tuple
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def fetch_finance_files(repo: str, branch: str, token: str) -> Tuple[str, str]:
    headers = {"Authorization": f"token {token}"}
    base_url = f"https://api.github.com/repos/{repo}/contents/"

    def get_file(filename: str) -> str:
        url = f"{base_url}{filename}?ref={branch}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        content = r.json()
        return base64.b64decode(content['content']).decode('utf-8')

    pl = get_file("files/quarterly_pnl.csv")
    bs = get_file("files/balance_sheet.md")
    return pl, bs

def update_github_issue(repo: str, token: str, content: str):
    headers = {"Authorization": f"token {token}"}
    issues_url = f"https://api.github.com/repos/{repo}/issues"

    sufix = datetime.today().strftime('%Y-%m-%d') + "-"+ str(uuid.uuid1()) 
    title = f"AI Financial Audit Discrepancies - {sufix}"
    r = requests.get(issues_url, headers=headers, params={"state": "open"})
    r.raise_for_status()
    issues = r.json()

    issue = next((i for i in issues if i["title"] == title), None)
    data = {"title": title, "body": content}

    if issue:
        url = f"{issues_url}/{issue['number']}"
        requests.patch(url, json=data, headers=headers)
    else:
        requests.post(issues_url, json=data, headers=headers)

def create_github_issue(repo:str, token:str, title:str, body:str):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": title,
        "body": body
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        issue = response.json()
        logger.info(f"Issue creado: {issue['html_url']}")
    else:
        logger.info(f"Error {response.status_code}: {response.text}")
