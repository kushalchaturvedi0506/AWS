# E-Commerce Order Processing Pipeline on AWS

## Overview
This project implements a serverless, event-driven order processing pipeline for e-commerce applications using AWS services. The architecture follows a modern ETL (Extract, Transform, Load) pattern orchestrated by AWS Step Functions.

## Architecture

**Event Flow:**
```
Order Event → EventBridge → Lambda Trigger → Step Functions
                                                    ↓
                                    ┌───────────────┼───────────────┐
                                    ↓               ↓               ↓
                              Lambda 1 (Extract) → Lambda 2 (Transform) → Lambda 3 (Load to S3)
```

## Components

### 1. **Event Source**
- E-commerce order events (new orders, updates, cancellations)
- Published to Amazon EventBridge

### 2. **Amazon EventBridge**
- Central event bus for order processing events
- Routes events based on patterns (order type, priority, etc.)
- Triggers the orchestration Lambda

### 3. **Lambda Trigger**
- Validates incoming events
- Initiates Step Function execution
- Handles event metadata and context

### 4. **AWS Step Functions** (Airflow Alternative)
- Orchestrates the ETL workflow
- Provides visual workflow monitoring
- Handles retries, error handling, and parallel processing
- State machine coordinates three Lambda functions

### 5. **Lambda 1 - Extract**
- Retrieves order details from source systems
- Fetches customer information from DynamoDB
- Retrieves product details and inventory status
- Validates data completeness

### 6. **Lambda 2 - Transform** (Glue-like)
- Cleanses and normalizes order data
- Enriches with business logic (tax calculation, discounts)
- Aggregates data from multiple sources
- Formats data for analytics and reporting
- Applies data quality rules

### 7. **Lambda 3 - Load**
- Writes processed data to S3 in partitioned structure
- Supports multiple formats (JSON, Parquet, CSV)
- Updates metadata catalog (AWS Glue Data Catalog)
- Triggers downstream analytics pipelines

## Features

- **Event-Driven Architecture**: Real-time order processing as events occur
- **Serverless**: No infrastructure management, auto-scaling
- **Resilient**: Built-in retry logic and error handling
- **Observable**: CloudWatch logging and X-Ray tracing
- **Cost-Effective**: Pay only for what you use
- **Extensible**: Easy to add new processing steps

## Project Structure

```
.
├── README.md
├── docs/
│   ├── architecture.md          # Detailed architecture documentation
│   └── deployment.md            # Deployment guide
├── infrastructure/
│   ├── terraform/               # Terraform IaC files
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── eventbridge.tf
│   │   ├── stepfunctions.tf
│   │   └── lambda.tf
│   └── cloudformation/          # Alternative CloudFormation templates
├── src/
│   ├── lambda-trigger/          # EventBridge trigger Lambda
│   ├── lambda-extract/          # Extract Lambda function
│   ├── lambda-transform/        # Transform Lambda function
│   └── lambda-load/             # Load Lambda function
├── stepfunctions/
│   └── order-processing-workflow.json
├── tests/
│   ├── unit/
│   └── integration/
└── scripts/
    └── deploy.sh
```

## Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0 (or AWS CLI for CloudFormation)
- Python 3.11+ for Lambda functions
- AWS CLI configured

## Quick Start

1. **Clone and configure:**
   ```bash
   cd "AWS Project Design"
   cp infrastructure/terraform/terraform.tfvars.example infrastructure/terraform/terraform.tfvars
   # Edit terraform.tfvars with your settings
   ```

2. **Deploy infrastructure:**
   ```bash
   cd infrastructure/terraform
   terraform init
   terraform plan
   terraform apply
   ```

3. **Test the pipeline:**
   ```bash
   aws events put-events --entries file://sample-events/order-created.json
   ```

## Monitoring

- **Step Functions Console**: View execution history and state transitions
- **CloudWatch Logs**: Lambda function logs organized by function name
- **CloudWatch Metrics**: Custom metrics for order processing rates
- **X-Ray**: Distributed tracing across the entire pipeline

## Cost Estimation

Based on 10,000 orders/day:
- EventBridge: ~$0.10/day
- Lambda: ~$2-5/day (depending on memory/duration)
- Step Functions: ~$0.25/day
- S3: ~$0.50/month (storage)
- **Total**: ~$75-90/month

## Security

- IAM roles with least privilege principle
- Encrypted data at rest (S3, DynamoDB)
- Encrypted data in transit (TLS)
- VPC endpoints for private communication (optional)
- Secrets Manager for sensitive credentials

## Future Enhancements

- [ ] Dead Letter Queue (DLQ) for failed orders
- [ ] SNS notifications for critical failures
- [ ] API Gateway for manual order submission
- [ ] Real-time analytics with Kinesis
- [ ] Data quality validation with AWS Deequ
- [ ] Cost allocation tags

## License

MIT License

## Contributors

- Kamal Chaturvedi
