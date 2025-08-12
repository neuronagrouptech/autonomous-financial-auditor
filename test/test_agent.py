from src.agent import run_audit

def test_run_audit(monkeypatch):
    def fake_fetch_finance_files(repo, branch, token):
        return ("|Revenue|1000|\n", "|Assets|5000|\n")

    def fake_parse(md):
        return {"Revenue": 1000.0}

    def fake_call_bedrock_llm(prompt):
        return "No discrepancies found."

    def fake_index_vector(text, meta):
        return "vec123"

    def fake_save_audit_metadata(data):
        pass

    def fake_update_github_issue(repo, token, content):
        pass

    monkeypatch.setattr("src.github_client.fetch_finance_files", fake_fetch_finance_files)
    monkeypatch.setattr("src.parser.parse_finance_markdown", fake_parse)
    monkeypatch.setattr("src.llm_bedrock_client.call_bedrock_llm", fake_call_bedrock_llm)
    monkeypatch.setattr("src.vector_db.index_vector", fake_index_vector)
    monkeypatch.setattr("src.dynamodb_client.save_audit_metadata", fake_save_audit_metadata)
    monkeypatch.setattr("src.github_client.update_github_issue", fake_update_github_issue)

    result = run_audit("repo", "main", "token", None)
    assert "No discrepancies" in result
