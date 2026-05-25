# modules/dynamodb/main.tf — DynamoDB NoSQL Table (Always Free Tier)
# AWS Free Tier: 25 GB storage, 25 RCU, 25 WCU — never expires.
# Encryption at rest is enforced. Billing mode is PROVISIONED to stay within free limits.

resource "aws_dynamodb_table" "main" {
  count = var.enable_dynamodb ? 1 : 0

  name         = var.table_name
  billing_mode = "PROVISIONED"
  hash_key     = var.hash_key

  # Stay within Always-Free limits (25 RCU / 25 WCU max)
  read_capacity  = var.read_capacity
  write_capacity = var.write_capacity

  attribute {
    name = var.hash_key
    type = var.hash_key_type
  }

  # Enforce encryption at rest (uses AWS-managed key — free)
  server_side_encryption {
    enabled = true
  }

  # Point-in-time recovery for data safety (free for first 5 tables)
  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = merge(var.tags, {
    Name = var.table_name
  })
}
