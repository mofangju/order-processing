terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = var.aws_access_key
  secret_key                  = var.aws_secret_key
  skip_credentials_validation = var.skip_credentials_validation
  skip_metadata_api_check     = var.skip_metadata_api_check
  skip_requesting_account_id  = var.skip_requesting_account_id
  skip_region_validation      = var.skip_region_validation

  dynamic "endpoints" {
    for_each = var.endpoint != null ? [1] : []
    content {
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
}