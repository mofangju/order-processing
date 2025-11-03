terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"   # LocalStack default
  secret_key                  = "test"   # LocalStack default
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_region_validation      = true

  endpoints {
    apigateway     = var.endpoint
    cloudformation = var.endpoint
    cloudwatch     = var.endpoint
    dynamodb       = var.endpoint
    ec2            = var.endpoint
    es             = var.endpoint
    elasticache    = var.endpoint
    firehose       = var.endpoint
    iam            = var.endpoint
    kinesis        = var.endpoint
    lambda         = var.endpoint
    rds            = var.endpoint
    redshift       = var.endpoint
    route53        = var.endpoint
    s3             = var.endpoint
    secretsmanager = var.endpoint
    ses            = var.endpoint
    sns            = var.endpoint
    sqs            = var.endpoint
    ssm            = var.endpoint
    stepfunctions  = var.endpoint
    sts            = var.endpoint
    xray           = var.endpoint
  }
}

# === SQS ===
resource "aws_sqs_queue" "order_queue" {
  name                        = "order-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 60
}

resource "aws_sqs_queue" "dlq" {
  name       = "order-queue-dlq.fifo"
  fifo_queue = true
}

resource "aws_sqs_queue_redrive_policy" "main" {
  queue_url = aws_sqs_queue.order_queue.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

# === DynamoDB ===
resource "aws_dynamodb_table" "orders" {
  name         = "Orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }
}

# === Outputs ===
output "sqs_queue_url" {
  value = aws_sqs_queue.order_queue.url
}

output "dynamodb_table" {
  value = aws_dynamodb_table.orders.name
}