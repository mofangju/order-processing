# DynamoDB table for storing orders
resource "aws_dynamodb_table" "orders" {
  name         = "${local.name_prefix}-Orders"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  # Point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-Orders"
    }
  )
}

