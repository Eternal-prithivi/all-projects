# modules/s3/main.tf — S3 Bucket (private ACL + AES256 encryption enforced)
# Public access is BLOCKED at all levels. Policy engine also enforces this as a hard block.

resource "aws_s3_bucket" "main" {
  count  = var.enable_s3 ? 1 : 0
  bucket = var.bucket_name

  tags = merge(var.tags, {
    Name = var.bucket_name
  })
}

# Block ALL public access — belt-and-suspenders with policy engine rule
resource "aws_s3_bucket_public_access_block" "main" {
  count  = var.enable_s3 ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# AES256 server-side encryption — always enforced
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  count  = var.enable_s3 ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versioning enabled for safety
resource "aws_s3_bucket_versioning" "main" {
  count  = var.enable_s3 ? 1 : 0
  bucket = aws_s3_bucket.main[0].id

  versioning_configuration {
    status = "Enabled"
  }
}
