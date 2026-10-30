locals {
  name_prefix  = "${var.project_name}-${var.environment}"
  cluster_name = "${local.name_prefix}-eks"

  availability_zones = slice(
    data.aws_availability_zones.available.names,
    0,
    var.availability_zone_count,
  )

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Service     = "withdrawal-soles"
    ManagedBy   = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}
