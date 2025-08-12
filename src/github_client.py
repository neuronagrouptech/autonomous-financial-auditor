import requests
import base64
from typing import Tuple

def fetch_finance_files(repo: str, branch: str, token: str) -> Tuple[str, str]:
    headers = {"Authorization": f"token {token}"}
    base_url = f"https://api.github.com/repos/{repo}/contents/"

    def get_file(filename: str) -> str:
        url = f"{base_url}{filename}?ref={branch}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        content = r.json()
        return base64.b64decode(content['content']).decode('utf-8')

    pl = get_file("Quarterly_P&L.md")
    bs = get_file("Balance_Sheet.md")
    return pl, bs

def update_github_issue(repo: str, token: str, content: str):
    headers = {"Authorization": f"token {token}"}
    issues_url = f"https://api.github.com/repos/{repo}/issues"

    r = requests.get(issues_url, headers=headers, params={"state": "open"})
    r.raise_for_status()
    issues = r.json()

    issue = next((i for i in issues if i["title"] == "AI Financial Audit Discrepancies"), None)
    data = {"title": "AI Financial Audit Discrepancies", "body": content}

    if issue:
        url = f"{issues_url}/{issue['number']}"
        requests.patch(url, json=data, headers=headers)
    else:
        requests.post(issues_url, json=data, headers=headers)
