# S3 Data Lake Bucket
resource "aws_s3_bucket" "data_lake" {
  bucket = var.data_lake_bucket_name != "" ? var.data_lake_bucket_name : "${var.project_name}-data-lake-${local.account_id}"
  
  tags = merge(
    local.common_tags,
    {
      Name = "Data Lake"
    }
  )
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Policy
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  
  rule {
    id     = "transition-to-glacier"
    status = "Enabled"
    
    filter {
      prefix = "orders/"
    }
    
    transition {
      days          = var.s3_lifecycle_glacier_days
      storage_class = "GLACIER"
    }
    
    expiration {
      days = var.s3_lifecycle_expiration_days
    }
  }
  
  rule {
    id     = "intelligent-tiering"
    status = "Enabled"
    
    filter {
      prefix = "analytics/"
    }
    
    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
  }
  
  rule {
    id     = "delete-old-logs"
    status = "Enabled"
    
    filter {
      prefix = "logs/"
    }
    
    expiration {
      days = 90
    }
  }
}

# KMS Key for S3 Encryption
resource "aws_kms_key" "data_lake" {
  description             = "KMS key for S3 data lake encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-data-lake-key"
    }
  )
}

resource "aws_kms_alias" "data_lake" {
  name          = "alias/${var.project_name}-data-lake"
  target_key_id = aws_kms_key.data_lake.key_id
}

# S3 Bucket for Lambda Code
resource "aws_s3_bucket" "lambda_code" {
  bucket = "${var.project_name}-lambda-code-${local.account_id}"
  
  tags = merge(
    local.common_tags,
    {
      Name = "Lambda Code"
    }
  )
}

resource "aws_s3_bucket_versioning" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Create folder structure in S3
resource "aws_s3_object" "folders" {
  for_each = toset([
    "orders/",
    "customers/",
    "products/",
    "analytics/",
    "logs/",
    "raw/",
    "processed/",
    "archived/"
  ])
  
  bucket = aws_s3_bucket.data_lake.id
  key    = each.value
}
