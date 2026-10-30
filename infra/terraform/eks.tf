resource "aws_eks_cluster" "this" {
  name     = local.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    security_group_ids      = [aws_security_group.cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  upgrade_policy {
    support_type = "STANDARD"
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler",
  ]

  tags = {
    Name = local.cluster_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_amazon_eks_cluster_policy,
  ]
}

resource "aws_launch_template" "nodes" {
  name_prefix = "${local.cluster_name}-node-"
  description = "EKS managed node group launch template"

  vpc_security_group_ids = [aws_security_group.nodes.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name = "${local.cluster_name}-node"
    }
  }

  tag_specifications {
    resource_type = "volume"

    tags = {
      Name = "${local.cluster_name}-node-volume"
    }
  }

  tags = {
    Name = "${local.cluster_name}-node"
  }
}

resource "aws_eks_node_group" "this" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${local.name_prefix}-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.node_instance_types
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"

  scaling_config {
    min_size     = var.node_min_size
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  launch_template {
    id      = aws_launch_template.nodes.id
    version = aws_launch_template.nodes.latest_version
  }

  labels = {
    role = "general"
  }

  tags = {
    Name = "${local.name_prefix}-nodes"
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_amazon_eks_worker_node_policy,
    aws_iam_role_policy_attachment.node_amazon_eks_cni_policy,
    aws_iam_role_policy_attachment.node_amazon_ecr_read_only,
    aws_security_group_rule.cluster_ingress_nodes_https,
    aws_security_group_rule.cluster_ingress_nat_https,
    aws_security_group_rule.eks_cluster_ingress_nodes_https,
    aws_security_group_rule.eks_cluster_ingress_nat_https,
    aws_security_group_rule.nodes_ingress_eks_cluster_ephemeral,
  ]

  lifecycle {
    precondition {
      condition     = var.node_desired_size >= var.node_min_size && var.node_desired_size <= var.node_max_size
      error_message = "node_desired_size must be between node_min_size and node_max_size."
    }
  }
}
