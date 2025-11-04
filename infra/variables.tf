# Provider Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS access key (for LocalStack, use 'test')"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS secret key (for LocalStack, use 'test')"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "endpoint" {
  description = "LocalStack endpoint URL (leave null for production AWS)"
  type        = string
  default     = null
}

variable "skip_credentials_validation" {
  description = "Skip AWS credentials validation (for LocalStack)"
  type        = bool
  default     = true
}

variable "skip_metadata_api_check" {
  description = "Skip AWS metadata API check (for LocalStack)"
  type        = bool
  default     = true
}

variable "skip_requesting_account_id" {
  description = "Skip requesting AWS account ID (for LocalStack)"
  type        = bool
  default     = true
}

variable "skip_region_validation" {
  description = "Skip AWS region validation (for LocalStack)"
  type        = bool
  default     = true
}

# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "order-processing"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# SQS Configuration
variable "sqs_visibility_timeout_seconds" {
  description = "Visibility timeout for SQS messages in seconds"
  type        = number
  default     = 60
}

variable "sqs_message_retention_seconds" {
  description = "Message retention period for SQS queue in seconds"
  type        = number
  default     = 345600 # 4 days
}

variable "sqs_max_receive_count" {
  description = "Maximum number of times a message can be received before moving to DLQ"
  type        = number
  default     = 3

  validation {
    condition     = var.sqs_max_receive_count > 0 && var.sqs_max_receive_count <= 1000
    error_message = "Max receive count must be between 1 and 1000."
  }
}

variable "dlq_message_retention_seconds" {
  description = "Message retention period for DLQ in seconds"
  type        = number
  default     = 1209600 # 14 days
}

# DynamoDB Configuration
variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "Billing mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable DynamoDB point-in-time recovery"
  type        = bool
  default     = true
}