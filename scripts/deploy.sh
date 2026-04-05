#!/usr/bin/env bash
# Deployment script for the order processing pipeline

set -e

echo "====================================="
echo "AWS E-Commerce Order Processing"
echo "Deployment Script"
echo "====================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is not installed"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "Error: aws CLI is not installed"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is not installed"; exit 1; }

echo "✓ All prerequisites met"
echo ""

# Change to terraform directory
cd infrastructure/terraform

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Validate configuration
echo "Validating Terraform configuration..."
terraform validate

# Plan deployment
echo "Planning deployment..."
terraform plan -out=tfplan

# Ask for confirmation
read -p "Do you want to proceed with deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Apply Terraform
echo "Deploying infrastructure..."
terraform apply tfplan

# Get outputs
echo ""
echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
terraform output

echo ""
echo "Next steps:"
echo "1. Run scripts/seed_sample_data.py to add test data"
echo "2. Run scripts/test_pipeline.py to test the pipeline"
echo "3. Check the CloudWatch dashboard for monitoring"
