resource "aws_db_subnet_group" "this" {
  name       = "${local.name_prefix}-postgres"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  description = "PostgreSQL access from EKS worker nodes"
  vpc_id      = aws_vpc.this.id

  tags = {
    Name = "${local.name_prefix}-rds"
  }
}

resource "aws_security_group_rule" "rds_ingress_nodes" {
  type                     = "ingress"
  description              = "PostgreSQL from EKS nodes"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.nodes.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}

resource "aws_db_instance" "this" {
  identifier = "${local.name_prefix}-postgres"

  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  multi_az                = var.db_multi_az
  backup_retention_period = var.db_backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  auto_minor_version_upgrade = true
  apply_immediately          = true
  copy_tags_to_snapshot      = true

  deletion_protection = var.db_deletion_protection
  skip_final_snapshot = var.db_skip_final_snapshot

  tags = {
    Name = "${local.name_prefix}-postgres"
  }
}
