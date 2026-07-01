output "alb_url" {
  description = "Application Load Balancer public URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_backend_url" {
  description = "ECR repository URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "ECR repository URL for the frontend image"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name — used in GitHub Actions CD workflow"
  value       = aws_ecs_cluster.main.name
}

output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

output "db_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the DATABASE_URL"
  value       = aws_secretsmanager_secret.db_url.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (ECS tasks + RDS)"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (ALB)"
  value       = aws_subnet.public[*].id
}
