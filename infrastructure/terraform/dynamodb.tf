# DynamoDB Table: Orders
resource "aws_dynamodb_table" "orders" {
  name           = "${var.project_name}-orders"
  billing_mode   = var.dynamodb_billing_mode
  hash_key       = "orderId"
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  attribute {
    name = "orderId"
    type = "S"
  }
  
  attribute {
    name = "customerId"
    type = "S"
  }
  
  attribute {
    name = "orderDate"
    type = "S"
  }
  
  global_secondary_index {
    name            = "CustomerIdIndex"
    hash_key        = "customerId"
    range_key       = "orderDate"
    projection_type = "ALL"
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  server_side_encryption {
    enabled = true
  }
  
  ttl {
    attribute_name = "expirationTime"
    enabled        = true
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-orders"
    }
  )
}

# DynamoDB Table: Customers
resource "aws_dynamodb_table" "customers" {
  name         = "${var.project_name}-customers"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "customerId"
  
  attribute {
    name = "customerId"
    type = "S"
  }
  
  attribute {
    name = "email"
    type = "S"
  }
  
  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  server_side_encryption {
    enabled = true
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-customers"
    }
  )
}

# DynamoDB Table: Execution Tracking (for idempotency)
resource "aws_dynamodb_table" "execution_tracking" {
  name         = "${var.project_name}-executions"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "orderId"
  range_key    = "eventId"
  
  attribute {
    name = "orderId"
    type = "S"
  }
  
  attribute {
    name = "eventId"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  server_side_encryption {
    enabled = true
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-executions"
    }
  )
}

# AWS Glue Database for Data Catalog
resource "aws_glue_catalog_database" "data_lake" {
  name        = var.project_name
  description = "E-commerce order processing data catalog"
}

# AWS Glue Table: Orders
resource "aws_glue_catalog_table" "orders" {
  name          = "orders"
  database_name = aws_glue_catalog_database.data_lake.name
  
  table_type = "EXTERNAL_TABLE"
  
  parameters = {
    EXTERNAL              = "TRUE"
    "parquet.compression" = "SNAPPY"
  }
  
  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake.id}/orders/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    
    ser_de_info {
      name                  = "ParquetHiveSerDe"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      
      parameters = {
        "serialization.format" = 1
      }
    }
    
    columns {
      name = "order_id"
      type = "string"
    }
    
    columns {
      name = "customer_id"
      type = "string"
    }
    
    columns {
      name = "total_amount"
      type = "double"
    }
    
    columns {
      name = "order_date"
      type = "timestamp"
    }
    
    columns {
      name = "status"
      type = "string"
    }
  }
  
  partition_keys {
    name = "year"
    type = "string"
  }
  
  partition_keys {
    name = "month"
    type = "string"
  }
  
  partition_keys {
    name = "day"
    type = "string"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", { stat = "Sum", label = "Started" }],
            [".", "ExecutionsSucceeded", { stat = "Sum", label = "Succeeded" }],
            [".", "ExecutionsFailed", { stat = "Sum", label = "Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "Step Function Executions"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum" }],
            [".", "Errors", { stat = "Sum" }],
            [".", "Throttles", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "Lambda Metrics (All Functions)"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = local.region
          title  = "Lambda Duration"
          view   = "timeSeries"
          stacked = false
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", 
             { stat = "Average", label = "DLQ Messages" }]
          ]
          period = 300
          stat   = "Average"
          region = local.region
          title  = "Dead Letter Queue"
          view   = "singleValue"
        }
      },
      {
        type = "log"
        properties = {
          query = <<-EOQ
            SOURCE '/aws/lambda/${aws_lambda_function.trigger.function_name}'
            SOURCE '/aws/lambda/${aws_lambda_function.extract.function_name}'
            SOURCE '/aws/lambda/${aws_lambda_function.transform.function_name}'
            SOURCE '/aws/lambda/${aws_lambda_function.load.function_name}'
            | fields @timestamp, @message
            | filter @message like /ERROR/
            | sort @timestamp desc
            | limit 20
          EOQ
          region = local.region
          title  = "Recent Errors"
        }
      }
    ]
  })
}
