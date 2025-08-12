resource "aws_iam_role" "lambda_exec" {
  name = "financial-auditor-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "financial_auditor" {
  function_name = "financial-auditor"

  s3_bucket = var.lambda_s3_bucket
  s3_key    = var.lambda_s3_key

  handler = "src.handler.lambda_handler"
  runtime = "python3.10"
  role    = aws_iam_role.lambda_exec.arn
  timeout = 30

  environment {
    variables = {
      GITHUB_REPO       = var.github_repo
      GITHUB_TOKEN      = var.github_token
      GITHUB_BRANCH     = "main"
      OPENSEARCH_HOST   = aws_opensearch_domain.financial_auditor.endpoint
      DYNAMODB_TABLE    = aws_dynamodb_table.audits_table.name
      AWS_REGION        = var.aws_region
    }
  }
}

resource "aws_api_gateway_rest_api" "financial_auditor_api" {
  name        = "financial-auditor-api"
  description = "API para disparar auditoría financiera"
}

resource "aws_api_gateway_resource" "audit" {
  rest_api_id = aws_api_gateway_rest_api.financial_auditor_api.id
  parent_id   = aws_api_gateway_rest_api.financial_auditor_api.root_resource_id
  path_part   = "audit"
}

resource "aws_api_gateway_method" "post_method" {
  rest_api_id   = aws_api_gateway_rest_api.financial_auditor_api.id
  resource_id   = aws_api_gateway_resource.audit.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.financial_auditor_api.id
  resource_id             = aws_api_gateway_resource.audit.id
  http_method             = aws_api_gateway_method.post_method.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.financial_auditor.invoke_arn
}

resource "aws_lambda_permission" "apigw_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.financial_auditor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.financial_auditor_api.execution_arn}/*/*"
}

resource "aws_opensearch_domain" "financial_auditor" {
  domain_name    = var.opensearch_domain_name
  engine_version = "OpenSearch_2.3"

  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
    volume_type = "gp3"
  }

  node_to_node_encryption {
    enabled = true
  }

  encrypt_at_rest {
    enabled = true
  }

  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "opensearch.index_vector_search.enabled" = "true"
  }
}

resource "aws_dynamodb_table" "audits_table" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audit_id"

  attribute {
    name = "audit_id"
    type = "S"
  }
}
