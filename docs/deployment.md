# Deployment Guide

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Terraform** >= 1.0 installed
4. **Python** 3.11+ installed
5. **Git** for version control

## Step 1: Clone and Configure

```bash
cd "c:\Users\kchaturvedi\OneDrive - MetLife\Desktop\AWS Project Design"
```

## Step 2: Configure Terraform Variables

Create a `terraform.tfvars` file:

```bash
cd infrastructure/terraform
notepad terraform.tfvars
```

Add the following content (customize as needed):

```hcl
aws_region     = "us-east-1"
environment    = "dev"
owner          = "kamal.chaturvedi"
project_name   = "ecommerce-order-processing"

# Lambda Configuration
lambda_memory_size = {
  trigger   = 256
  extract   = 512
  transform = 1024
  load      = 512
}

lambda_timeout = {
  trigger   = 30
  extract   = 60
  transform = 120
  load      = 60
}

lambda_reserved_concurrent_executions = 100

# S3 Configuration
data_lake_bucket_name = ""  # Leave empty for auto-generation

# Monitoring
enable_xray_tracing   = true
log_retention_days    = 30
alarm_email           = "your-email@example.com"

# DynamoDB
dynamodb_billing_mode = "PAY_PER_REQUEST"
```

## Step 3: Install Lambda Dependencies

Each Lambda function needs its dependencies packaged:

```powershell
# Install dependencies for each Lambda function
$functions = @("lambda-trigger", "lambda-extract", "lambda-transform", "lambda-load")

foreach ($func in $functions) {
    Write-Host "Installing dependencies for $func..."
    cd "..\..\src\$func"
    
    # Create package directory
    New-Item -ItemType Directory -Force -Path package
    
    # Install dependencies
    pip install -r requirements.txt -t package/
    
    # Copy handler
    Copy-Item handler.py package/
    
    Write-Host "Completed $func"
}

cd ..\..\infrastructure\terraform
```

## Step 4: Initialize Terraform

```bash
terraform init
```

This will:
- Download required providers (AWS, Archive)
- Set up backend (if configured)
- Initialize modules

## Step 5: Review Terraform Plan

```bash
terraform plan
```

Review the resources that will be created:
- EventBridge event bus and rules
- Lambda functions (4)
- Step Functions state machine
- S3 buckets (data lake, Lambda code)
- DynamoDB tables (3)
- IAM roles and policies
- CloudWatch logs and alarms
- Glue Data Catalog

## Step 6: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. Deployment takes approximately 5-10 minutes.

## Step 7: Verify Deployment

```powershell
# Get outputs
terraform output

# Expected outputs:
# - eventbridge_bus_arn
# - step_function_arn
# - lambda_trigger_arn
# - data_lake_bucket_name
# - test_event_command
```

## Step 8: Seed Sample Data (Optional)

Create sample customer and order data in DynamoDB:

```powershell
# Run the seed script
cd ..\..\scripts
python seed_sample_data.py
```

## Step 9: Test the Pipeline

### Option 1: Using AWS CLI

```powershell
# Get the EventBridge bus name from Terraform output
$BUS_NAME = terraform output -raw eventbridge_bus_name

# Send a test event
aws events put-events --entries file://../../sample-events/order-created.json
```

### Option 2: Using the AWS Console

1. Go to EventBridge console
2. Select your event bus
3. Click "Send events"
4. Use the sample event from `sample-events/order-created.json`

### Option 3: Using the Test Script

```powershell
cd ..\..\scripts
python test_pipeline.py
```

## Step 10: Monitor Execution

### CloudWatch Logs

```powershell
# View logs for trigger function
aws logs tail /aws/lambda/ecommerce-order-processing-dev-trigger --follow

# View logs for step function
aws logs tail /aws/stepfunctions/ecommerce-order-processing-dev-workflow --follow
```

### Step Functions Console

1. Go to Step Functions console
2. Click on the state machine name
3. View execution history
4. Click on an execution to see the visual workflow

### CloudWatch Dashboard

Navigate to the dashboard URL from Terraform output:

```powershell
terraform output cloudwatch_dashboard_url
```

## Troubleshooting

### Lambda Package Too Large

If Lambda packages exceed 50MB:

```powershell
# Use Lambda layers for common dependencies
# Create a layer with pandas and pyarrow
cd src
New-Item -ItemType Directory -Force -Path lambda-layer/python
pip install pandas pyarrow -t lambda-layer/python/
cd lambda-layer
Compress-Archive -Path python -DestinationPath ../lambda-layer.zip
```

Then create a Lambda layer in AWS and attach it to the load function.

### Permission Errors

Ensure your AWS credentials have the following permissions:
- IAM: Create/Update roles and policies
- Lambda: Create/Update functions
- S3: Create buckets and objects
- EventBridge: Create event buses and rules
- Step Functions: Create state machines
- DynamoDB: Create tables
- CloudWatch: Create log groups and alarms
- Glue: Create databases and tables

### EventBridge Not Triggering

Check:
1. Event pattern matches your event structure
2. Lambda permission is set correctly
3. Check CloudWatch Logs for errors

```powershell
# Test the trigger directly
aws lambda invoke --function-name ecommerce-order-processing-dev-trigger --payload file://test-payload.json response.json
```

### Step Function Failures

1. Check execution history in Step Functions console
2. Review CloudWatch Logs for each Lambda function
3. Check IAM permissions for Step Functions role
4. Verify Lambda functions are not timing out

## Updating the Deployment

### Code Changes

```powershell
# Re-package Lambda functions
cd src/lambda-extract
pip install -r requirements.txt -t package/
Copy-Item handler.py package/

# Apply changes
cd ../../infrastructure/terraform
terraform apply
```

### Infrastructure Changes

```powershell
# Modify Terraform files
# Then apply changes
terraform apply
```

## Cleanup

To remove all resources:

```powershell
cd infrastructure/terraform
terraform destroy
```

**Warning**: This will delete:
- All Lambda functions
- S3 buckets (if empty)
- DynamoDB tables
- EventBridge rules
- Step Functions state machines
- CloudWatch logs (after retention period)

To preserve data:
1. Back up S3 data
2. Export DynamoDB tables
3. Save CloudWatch logs

## Cost Estimation

Monthly costs for 10,000 orders/day:

| Service | Cost |
|---------|------|
| EventBridge | $0.30 |
| Lambda (4 functions) | $2.40 |
| Step Functions | $7.50 |
| S3 Storage (10GB) | $0.23 |
| DynamoDB (on-demand) | $10.00 |
| CloudWatch Logs | $0.50 |
| **Total** | **~$20.93/month** |

Scale up to 100,000 orders/day: **~$200/month**

## Next Steps

1. **Set Up CI/CD**: Integrate with GitHub Actions or AWS CodePipeline
2. **Add Monitoring**: Set up custom CloudWatch metrics and dashboards
3. **Implement Alarms**: Configure SNS notifications for failures
4. **Add Testing**: Unit tests and integration tests
5. **Security Review**: Implement VPC, encryption at rest/transit
6. **Performance Tuning**: Optimize Lambda memory and timeout settings
7. **Data Retention**: Configure S3 lifecycle policies
8. **Disaster Recovery**: Set up cross-region replication

## Support

For issues or questions:
- Check CloudWatch Logs
- Review AWS service quotas
- Consult AWS documentation
- Contact AWS Support (if applicable)
