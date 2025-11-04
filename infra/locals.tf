locals {
  # Common tags applied to all resources
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }

  # Resource naming
  name_prefix = "${var.project_name}-${var.environment}"
}

