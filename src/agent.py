from typing import Dict, Optional
from github_client import fetch_finance_files, update_github_issue
from parser import parse_finance_markdown
from llm_bedrock_client import call_bedrock_llm
from vector_db import index_vector
from dynamodb_client import save_audit_metadata

def run_audit(repo: str, branch: str, github_token: str, context: Optional[object] = None) -> str:
    # Descargar archivos financieros
    pl_content, bs_content = fetch_finance_files(repo, branch, github_token)

    # Parsear documentos
    pl_data = parse_finance_markdown(pl_content)
    bs_data = parse_finance_markdown(bs_content)

    # Crear prompt para LLM
    prompt = (
        f"Compara estos datos financieros y detecta inconsistencias:\n"
        f"P&L: {pl_data}\nBalance Sheet: {bs_data}\n"
        f"Indica discrepancias y sugiere correcciones."
    )

    # Consultar AWS Bedrock LLM
    llm_response = call_bedrock_llm(prompt)

    # Indexar en OpenSearch Vector DB
    vector_id = index_vector(llm_response, {"repo": repo, "branch": branch})

    # Guardar metadata en DynamoDB
    save_audit_metadata({
        "repo": repo,
        "branch": branch,
        "result": llm_response,
        "vector_id": vector_id,
        "timestamp": None if not context else context.aws_request_id
    })

    # Crear o actualizar issue en GitHub
    update_github_issue(repo, github_token, llm_response)

    return llm_response
