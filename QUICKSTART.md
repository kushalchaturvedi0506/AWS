# Quick Start Guide

## Overview
This project implements a serverless order processing pipeline on AWS using EventBridge, Lambda, and Step Functions.

## Architecture Flow
```
Order Event → EventBridge → Lambda Trigger → Step Functions
                                                    ↓
                            Extract → Transform → Load to S3
```

## Prerequisites
- AWS Account
- AWS CLI configured
- Terraform >= 1.0
- Python 3.11+

## Quick Deploy (5 steps)

### 1. Configure
```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings
```

### 2. Deploy
```bash
terraform init
terraform apply
```

### 3. Seed Test Data
```bash
cd ../../scripts
python seed_sample_data.py
```

### 4. Test Pipeline
```bash
python test_pipeline.py
```

### 5. Monitor
```bash
# View the CloudWatch dashboard
terraform output cloudwatch_dashboard_url
```

## Send Test Event

```bash
aws events put-events \
  --entries file://sample-events/order-created.json
```

## Project Structure
```
.
├── docs/                      # Documentation
│   ├── architecture.md        # Detailed architecture
│   └── deployment.md          # Deployment guide
├── infrastructure/terraform/  # Infrastructure as Code
│   ├── main.tf               # Main configuration
│   ├── lambda.tf             # Lambda functions
│   ├── stepfunctions.tf      # Step Functions
│   ├── eventbridge.tf        # EventBridge config
│   └── s3.tf                 # S3 buckets
├── src/                       # Lambda function code
│   ├── lambda-trigger/       # EventBridge trigger
│   ├── lambda-extract/       # Extract data
│   ├── lambda-transform/     # Transform data
│   └── lambda-load/          # Load to S3
├── sample-events/             # Sample EventBridge events
└── scripts/                   # Utility scripts
```

## Key Components

### EventBridge
- Event bus for order events
- Rules for routing events
- Archive for event replay

### Lambda Functions
1. **Trigger**: Validates events, starts Step Function
2. **Extract**: Fetches data from DynamoDB, APIs
3. **Transform**: Cleanses, enriches data
4. **Load**: Writes to S3 in Parquet format

### Step Functions
Orchestrates ETL workflow with:
- Retry logic
- Error handling
- Visual monitoring

### S3 Data Lake
Partitioned structure:
```
s3://bucket/orders/year=2026/month=04/day=05/hour=10/
```

### DynamoDB Tables
- Orders: Order records
- Customers: Customer profiles
- Executions: Idempotency tracking

## Monitoring

### CloudWatch Logs
```bash
# Trigger function
aws logs tail /aws/lambda/ecommerce-order-processing-dev-trigger --follow

# Step Function
aws logs tail /aws/stepfunctions/ecommerce-order-processing-dev-workflow --follow
```

### Step Functions Console
1. Go to AWS Console → Step Functions
2. View execution history
3. Click execution for visual workflow

## Cost Estimate
~$20-25/month for 10,000 orders/day

## Common Issues

### Lambda Package Too Large
Use Lambda layers for pandas/pyarrow

### Permission Errors
Check IAM role policies

### EventBridge Not Triggering
Verify event pattern matches

## Cleanup
```bash
terraform destroy
```

## Next Steps
1. Set up CI/CD pipeline
2. Add more test coverage
3. Configure production settings
4. Set up cross-region replication
5. Implement data quality checks

## Support
- Check [Architecture Docs](docs/architecture.md)
- Review [Deployment Guide](docs/deployment.md)
- Review CloudWatch Logs
- Check AWS service quotas

## Sample Output

After running test_pipeline.py:
```
============================================================
Sending test order event...
============================================================
Order ID: TEST-20260405103045
Customer ID: CUST-TEST-001
Amount: $299.99
✓ Event sent successfully!

Waiting for execution to start (timeout: 60s)...
✓ Found execution: TEST-20260405103045-20260405103046

============================================================
Monitoring execution...
============================================================

Status: RUNNING
Status: SUCCEEDED

✓ Execution completed successfully!

============================================================
Execution Summary
============================================================
S3 Location: s3://bucket/orders/year=2026/month=04/day=05/...
Records Count: 3

============================================================
✓ TEST PASSED - Pipeline executed successfully!
============================================================
```
