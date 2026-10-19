resource "aws_s3_bucket" "shopanalysis" {
  bucket = "shopanalysis-777311273388-us-east-2"

  tags = {
    Project   = "ShopAnalysis"
    ManagedBy = "Terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "shopanalysis" {
  bucket = aws_s3_bucket.shopanalysis.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "shopanalysis" {
  bucket = aws_s3_bucket.shopanalysis.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "shopanalysis" {
  bucket = aws_s3_bucket.shopanalysis.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "shopanalysis" {
  bucket = aws_s3_bucket.shopanalysis.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "shopanalysis" {
  bucket = aws_s3_bucket.shopanalysis.id

  rule {
    id     = "expire-noncurrent-versions-after-30-days"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  depends_on = [
    aws_s3_bucket_versioning.shopanalysis
  ]
}
