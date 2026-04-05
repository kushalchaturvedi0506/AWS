output "eventbridge_bus_name" {
  description = "EventBridge bus name"
  value       = aws_cloudwatch_event_bus.orders.name
}

output "eventbridge_bus_arn" {
  description = "EventBridge bus ARN"
  value       = aws_cloudwatch_event_bus.orders.arn
}

output "step_function_arn" {
  description = "Step Function state machine ARN"
  value       = aws_sfn_state_machine.order_processing.arn
}

output "step_function_name" {
  description = "Step Function state machine name"
  value       = aws_sfn_state_machine.order_processing.name
}

output "lambda_trigger_arn" {
  description = "Lambda trigger function ARN"
  value       = aws_lambda_function.trigger.arn
}

output "lambda_trigger_name" {
  description = "Lambda trigger function name"
  value       = aws_lambda_function.trigger.function_name
}

output "lambda_extract_arn" {
  description = "Lambda extract function ARN"
  value       = aws_lambda_function.extract.arn
}

output "lambda_transform_arn" {
  description = "Lambda transform function ARN"
  value       = aws_lambda_function.transform.arn
}

output "lambda_load_arn" {
  description = "Lambda load function ARN"
  value       = aws_lambda_function.load.arn
}

output "data_lake_bucket_name" {
  description = "S3 data lake bucket name"
  value       = aws_s3_bucket.data_lake.id
}

output "data_lake_bucket_arn" {
  description = "S3 data lake bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}

output "dynamodb_orders_table_name" {
  description = "DynamoDB orders table name"
  value       = aws_dynamodb_table.orders.name
}

output "dynamodb_customers_table_name" {
  description = "DynamoDB customers table name"
  value       = aws_dynamodb_table.customers.name
}

output "test_event_command" {
  description = "AWS CLI command to send a test event"
  value       = <<-EOT
    aws events put-events --entries '[{
      "Source": "ecommerce.orders",
      "DetailType": "OrderCreated",
      "Detail": "{\"orderId\":\"TEST-001\",\"customerId\":\"CUST-001\",\"totalAmount\":299.99}",
      "EventBusName": "${aws_cloudwatch_event_bus.orders.name}"
    }]'
  EOT
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
