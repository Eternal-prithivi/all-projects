# modules/iam/main.tf — IAM Role with Least Privilege
# SECURITY: No wildcard (*) permissions. Policy engine blocks IAM wildcard as a hard block.

resource "aws_iam_role" "main" {
  count = var.enable_iam ? 1 : 0
  name  = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Least privilege — specific read actions only, no wildcard resources
resource "aws_iam_role_policy" "main" {
  count = var.enable_iam ? 1 : 0
  name  = "${var.role_name}-policy"
  role  = aws_iam_role.main[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = "arn:aws:s3:::${var.s3_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "main" {
  count = var.enable_iam ? 1 : 0
  name  = "${var.role_name}-profile"
  role  = aws_iam_role.main[0].name
}
