# EventBridge Event Bus
resource "aws_cloudwatch_event_bus" "orders" {
  name = "${var.project_name}-${var.environment}"
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-event-bus"
    }
  )
}

# EventBridge Archive (for replay capability)
resource "aws_cloudwatch_event_archive" "orders" {
  name             = "${var.project_name}-archive"
  event_source_arn = aws_cloudwatch_event_bus.orders.arn
  retention_days   = var.eventbridge_archive_retention_days
  
  description = "Archive for order processing events"
}

# EventBridge Rule: Order Created Events
resource "aws_cloudwatch_event_rule" "order_created" {
  name           = "${var.project_name}-order-created"
  description    = "Trigger on OrderCreated events"
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  
  event_pattern = jsonencode({
    source      = ["ecommerce.orders"]
    detail-type = ["OrderCreated"]
  })
  
  tags = local.common_tags
}

# EventBridge Rule: Order Updated Events
resource "aws_cloudwatch_event_rule" "order_updated" {
  name           = "${var.project_name}-order-updated"
  description    = "Trigger on OrderUpdated events"
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  
  event_pattern = jsonencode({
    source      = ["ecommerce.orders"]
    detail-type = ["OrderUpdated"]
  })
  
  tags = local.common_tags
}

# EventBridge Rule: High Priority Orders
resource "aws_cloudwatch_event_rule" "high_priority_orders" {
  name           = "${var.project_name}-high-priority"
  description    = "Trigger on high-value orders (>$1000)"
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  
  event_pattern = jsonencode({
    source      = ["ecommerce.orders"]
    detail-type = ["OrderCreated"]
    detail = {
      totalAmount = [{ numeric = [">", 1000] }]
    }
  })
  
  tags = local.common_tags
}

# EventBridge Target: Lambda Trigger for Order Created
resource "aws_cloudwatch_event_target" "order_created_trigger" {
  rule           = aws_cloudwatch_event_rule.order_created.name
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  arn            = aws_lambda_function.trigger.arn
  
  retry_policy {
    maximum_event_age       = 3600  # 1 hour
    maximum_retry_attempts  = 3
  }
  
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}

# EventBridge Target: Lambda Trigger for Order Updated
resource "aws_cloudwatch_event_target" "order_updated_trigger" {
  rule           = aws_cloudwatch_event_rule.order_updated.name
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  arn            = aws_lambda_function.trigger.arn
  
  retry_policy {
    maximum_event_age       = 3600
    maximum_retry_attempts  = 3
  }
  
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}

# EventBridge Target: Lambda Trigger for High Priority Orders
resource "aws_cloudwatch_event_target" "high_priority_trigger" {
  rule           = aws_cloudwatch_event_rule.high_priority_orders.name
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  arn            = aws_lambda_function.trigger.arn
  
  retry_policy {
    maximum_event_age       = 3600
    maximum_retry_attempts  = 3
  }
}

# Lambda permission for EventBridge to invoke trigger function
resource "aws_lambda_permission" "eventbridge_trigger_order_created" {
  statement_id  = "AllowEventBridgeOrderCreated"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.order_created.arn
}

resource "aws_lambda_permission" "eventbridge_trigger_order_updated" {
  statement_id  = "AllowEventBridgeOrderUpdated"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.order_updated.arn
}

resource "aws_lambda_permission" "eventbridge_trigger_high_priority" {
  statement_id  = "AllowEventBridgeHighPriority"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.high_priority_orders.arn
}

# Dead Letter Queue for failed events
resource "aws_sqs_queue" "dlq" {
  name                       = "${var.project_name}-dlq"
  message_retention_seconds  = 1209600  # 14 days
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-dlq"
    }
  )
}

# SQS Queue Policy
resource "aws_sqs_queue_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.dlq.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = [
              aws_cloudwatch_event_rule.order_created.arn,
              aws_cloudwatch_event_rule.order_updated.arn
            ]
          }
        }
      }
    ]
  })
}

# CloudWatch Alarm for DLQ messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when messages appear in DLQ"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}
