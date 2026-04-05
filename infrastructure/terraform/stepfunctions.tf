# Step Functions State Machine
resource "aws_sfn_state_machine" "order_processing" {
  name     = "${var.project_name}-workflow"
  role_arn = aws_iam_role.step_functions.arn
  
  definition = jsonencode({
    Comment = "E-commerce Order Processing ETL Pipeline"
    StartAt = "ExtractData"
    States = {
      ExtractData = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.extract.arn
          Payload = {
            "orderId.$"      = "$.detail.orderId"
            "customerId.$"   = "$.detail.customerId"
            "orderDetails.$" = "$.detail"
            "eventTime.$"    = "$.time"
          }
        }
        ResultPath = "$.extractResult"
        ResultSelector = {
          "statusCode.$" = "$.Payload.statusCode"
          "data.$"       = "$.Payload.body"
        }
        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "HandleExtractError"
            ResultPath  = "$.error"
          }
        ]
        Next = "TransformData"
      }
      
      TransformData = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.transform.arn
          Payload = {
            "orderId.$"        = "$.detail.orderId"
            "extractedData.$"  = "$.extractResult.data"
            "eventTime.$"      = "$.time"
          }
        }
        ResultPath = "$.transformResult"
        ResultSelector = {
          "statusCode.$" = "$.Payload.statusCode"
          "data.$"       = "$.Payload.body"
        }
        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "HandleTransformError"
            ResultPath  = "$.error"
          }
        ]
        Next = "LoadData"
      }
      
      LoadData = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.load.arn
          Payload = {
            "orderId.$"         = "$.detail.orderId"
            "transformedData.$" = "$.transformResult.data"
            "eventTime.$"       = "$.time"
          }
        }
        ResultPath = "$.loadResult"
        ResultSelector = {
          "statusCode.$"  = "$.Payload.statusCode"
          "s3Location.$"  = "$.Payload.body.s3Location"
          "recordsCount.$" = "$.Payload.body.recordsCount"
        }
        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "HandleLoadError"
            ResultPath  = "$.error"
          }
        ]
        Next = "ProcessingSuccess"
      }
      
      ProcessingSuccess = {
        Type = "Succeed"
      }
      
      HandleExtractError = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = var.alarm_email != "" ? aws_sns_topic.alerts[0].arn : "arn:aws:sns:${local.region}:${local.account_id}:dummy"
          Subject  = "Order Processing Failed - Extract Stage"
          Message = {
            "error.$"    = "$.error.Error"
            "cause.$"    = "$.error.Cause"
            "orderId.$"  = "$.detail.orderId"
            "stage"      = "Extract"
          }
        }
        Next = "ProcessingFailed"
      }
      
      HandleTransformError = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = var.alarm_email != "" ? aws_sns_topic.alerts[0].arn : "arn:aws:sns:${local.region}:${local.account_id}:dummy"
          Subject  = "Order Processing Failed - Transform Stage"
          Message = {
            "error.$"    = "$.error.Error"
            "cause.$"    = "$.error.Cause"
            "orderId.$"  = "$.detail.orderId"
            "stage"      = "Transform"
          }
        }
        Next = "ProcessingFailed"
      }
      
      HandleLoadError = {
        Type = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = var.alarm_email != "" ? aws_sns_topic.alerts[0].arn : "arn:aws:sns:${local.region}:${local.account_id}:dummy"
          Subject  = "Order Processing Failed - Load Stage"
          Message = {
            "error.$"    = "$.error.Error"
            "cause.$"    = "$.error.Cause"
            "orderId.$"  = "$.detail.orderId"
            "stage"      = "Load"
          }
        }
        Next = "ProcessingFailed"
      }
      
      ProcessingFailed = {
        Type  = "Fail"
        Error = "OrderProcessingError"
        Cause = "Order processing pipeline failed"
      }
    }
  })
  
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  
  tracing_configuration {
    enabled = var.enable_xray_tracing
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-state-machine"
    }
  )
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.project_name}-workflow"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# CloudWatch Alarm for Step Function Failures
resource "aws_cloudwatch_metric_alarm" "step_function_failures" {
  alarm_name          = "${var.project_name}-step-function-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "2"
  alarm_description   = "Alert when Step Function has failures"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    StateMachineArn = aws_sfn_state_machine.order_processing.arn
  }
}

resource "aws_cloudwatch_metric_alarm" "step_function_timeout" {
  alarm_name          = "${var.project_name}-step-function-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Average"
  threshold           = "60000"  # 60 seconds in milliseconds
  alarm_description   = "Alert when Step Function execution takes too long"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  
  dimensions = {
    StateMachineArn = aws_sfn_state_machine.order_processing.arn
  }
}
