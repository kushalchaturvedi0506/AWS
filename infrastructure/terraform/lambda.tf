# Archive Lambda functions code
data "archive_file" "lambda_trigger" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda-trigger"
  output_path = "${path.module}/.terraform/tmp/lambda-trigger.zip"
}

data "archive_file" "lambda_extract" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda-extract"
  output_path = "${path.module}/.terraform/tmp/lambda-extract.zip"
}

data "archive_file" "lambda_transform" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda-transform"
  output_path = "${path.module}/.terraform/tmp/lambda-transform.zip"
}

data "archive_file" "lambda_load" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda-load"
  output_path = "${path.module}/.terraform/tmp/lambda-load.zip"
}

# ========================================
# Lambda Trigger Function
# ========================================

resource "aws_lambda_function" "trigger" {
  filename         = data.archive_file.lambda_trigger.output_path
  function_name    = "${var.project_name}-trigger"
  role            = aws_iam_role.lambda_trigger.arn
  handler         = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_trigger.output_base64sha256
  runtime         = local.lambda_runtime
  timeout         = var.lambda_timeout["trigger"]
  memory_size     = var.lambda_memory_size["trigger"]
  
  environment {
    variables = {
      ENVIRONMENT            = var.environment
      STATE_MACHINE_ARN      = aws_sfn_state_machine.order_processing.arn
      EXECUTION_TABLE_NAME   = aws_dynamodb_table.execution_tracking.name
      POWERTOOLS_SERVICE_NAME = "order-trigger"
      LOG_LEVEL              = "INFO"
    }
  }
  
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-trigger"
    }
  )
}

resource "aws_cloudwatch_log_group" "lambda_trigger" {
  name              = "/aws/lambda/${aws_lambda_function.trigger.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# ========================================
# Lambda Extract Function
# ========================================

resource "aws_lambda_function" "extract" {
  filename         = data.archive_file.lambda_extract.output_path
  function_name    = "${var.project_name}-extract"
  role            = aws_iam_role.lambda_extract.arn
  handler         = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_extract.output_base64sha256
  runtime         = local.lambda_runtime
  timeout         = var.lambda_timeout["extract"]
  memory_size     = var.lambda_memory_size["extract"]
  
  environment {
    variables = {
      ENVIRONMENT            = var.environment
      ORDERS_TABLE_NAME      = aws_dynamodb_table.orders.name
      CUSTOMERS_TABLE_NAME   = aws_dynamodb_table.customers.name
      POWERTOOLS_SERVICE_NAME = "order-extract"
      LOG_LEVEL              = "INFO"
    }
  }
  
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  reserved_concurrent_executions = var.lambda_reserved_concurrent_executions
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-extract"
    }
  )
}

resource "aws_cloudwatch_log_group" "lambda_extract" {
  name              = "/aws/lambda/${aws_lambda_function.extract.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# ========================================
# Lambda Transform Function
# ========================================

resource "aws_lambda_function" "transform" {
  filename         = data.archive_file.lambda_transform.output_path
  function_name    = "${var.project_name}-transform"
  role            = aws_iam_role.lambda_transform.arn
  handler         = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_transform.output_base64sha256
  runtime         = local.lambda_runtime
  timeout         = var.lambda_timeout["transform"]
  memory_size     = var.lambda_memory_size["transform"]
  
  environment {
    variables = {
      ENVIRONMENT            = var.environment
      POWERTOOLS_SERVICE_NAME = "order-transform"
      LOG_LEVEL              = "INFO"
    }
  }
  
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  reserved_concurrent_executions = var.lambda_reserved_concurrent_executions
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-transform"
    }
  )
}

resource "aws_cloudwatch_log_group" "lambda_transform" {
  name              = "/aws/lambda/${aws_lambda_function.transform.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# ========================================
# Lambda Load Function
# ========================================

resource "aws_lambda_function" "load" {
  filename         = data.archive_file.lambda_load.output_path
  function_name    = "${var.project_name}-load"
  role            = aws_iam_role.lambda_load.arn
  handler         = "handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_load.output_base64sha256
  runtime         = local.lambda_runtime
  timeout         = var.lambda_timeout["load"]
  memory_size     = var.lambda_memory_size["load"]
  
  environment {
    variables = {
      ENVIRONMENT            = var.environment
      DATA_LAKE_BUCKET       = aws_s3_bucket.data_lake.id
      GLUE_DATABASE_NAME     = var.project_name
      POWERTOOLS_SERVICE_NAME = "order-load"
      LOG_LEVEL              = "INFO"
    }
  }
  
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  reserved_concurrent_executions = var.lambda_reserved_concurrent_executions
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-load"
    }
  )
}

resource "aws_cloudwatch_log_group" "lambda_load" {
  name              = "/aws/lambda/${aws_lambda_function.load.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# ========================================
# Lambda Function Alarms
# ========================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    trigger   = aws_lambda_function.trigger.function_name
    extract   = aws_lambda_function.extract.function_name
    transform = aws_lambda_function.transform.function_name
    load      = aws_lambda_function.load.function_name
  }
  
  alarm_name          = "${each.value}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when ${each.value} has more than 5 errors"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    FunctionName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = {
    extract   = aws_lambda_function.extract.function_name
    transform = aws_lambda_function.transform.function_name
    load      = aws_lambda_function.load.function_name
  }
  
  alarm_name          = "${each.value}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when ${each.value} is throttled"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    FunctionName = each.value
  }
}
