# ─── DB Subnet Group ─────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${var.app_name}-db-subnet-group" }
}

# ─── RDS Parameter Group (enables pgvector) ───────────────────────────────────

resource "aws_db_parameter_group" "postgres" {
  family      = "postgres16"
  name        = "${var.app_name}-pg16-params"
  description = "PostgreSQL 16 with pgvector support"

  # Required for pgvector shared_preload_libraries
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  tags = { Name = "${var.app_name}-pg-params" }
}

# ─── RDS Instance ─────────────────────────────────────────────────────────────

resource "aws_db_instance" "postgres" {
  identifier = "${var.app_name}-postgres"

  engine               = "postgres"
  engine_version       = "16.4"
  instance_class       = var.db_instance_class
  allocated_storage    = 20
  max_allocated_storage = 100   # autoscaling up to 100 GB
  storage_type         = "gp3"
  storage_encrypted    = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  parameter_group_name   = aws_db_parameter_group.postgres.name
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Backups
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Availability
  multi_az               = var.environment == "production"
  publicly_accessible    = false
  deletion_protection    = var.environment == "production"
  skip_final_snapshot    = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.app_name}-final-snapshot" : null

  tags = { Name = "${var.app_name}-postgres" }
}

# ─── Store DB connection string in Secrets Manager ───────────────────────────

resource "aws_secretsmanager_secret" "db_url" {
  name        = "${var.app_name}/database-url"
  description = "PostgreSQL async connection URL for the AIOP backend"
  tags        = { Name = "${var.app_name}-db-url" }
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
}
