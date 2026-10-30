resource "aws_ecr_repository" "withdrawal_soles" {
  name                 = "${local.name_prefix}/withdrawal-soles"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-withdrawal-soles"
  }
}
