terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  # Store state in S3 — uncomment after creating the bucket
  # backend "s3" {
  #   bucket         = "aiop-terraform-state"
  #   key            = "prod/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "aiop-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AIOP"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ─── Data sources ────────────────────────────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
