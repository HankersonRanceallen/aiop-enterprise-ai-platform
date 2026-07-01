variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "app_name" {
  description = "Application name — used as prefix for all resources"
  type        = string
  default     = "aiop"
}

# ─── Network ─────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ─── RDS ─────────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.medium"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "aiop_db"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "aiop"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password — store in AWS Secrets Manager"
  type        = string
  sensitive   = true
}

# ─── ECS ─────────────────────────────────────────────────────────────────────

variable "backend_cpu" {
  description = "CPU units for backend Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Memory (MB) for backend Fargate task"
  type        = number
  default     = 2048
}

variable "frontend_cpu" {
  type    = number
  default = 512
}

variable "frontend_memory" {
  type    = number
  default = 1024
}

variable "backend_desired_count" {
  description = "Number of backend task replicas"
  type        = number
  default     = 2
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}

# ─── App secrets (set via tfvars or CI env vars) ─────────────────────────────

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "app_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}
