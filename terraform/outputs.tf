output "api_endpoint" {
  value = aws_api_gateway_rest_api.financial_auditor_api.execution_arn
}

output "lambda_function_name" {
  value = aws_lambda_function.financial_auditor.function_name
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.financial_auditor.endpoint
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.audits_table.name
}
