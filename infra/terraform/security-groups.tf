resource "aws_security_group" "cluster" {
  name_prefix = "${local.cluster_name}-cluster-"
  description = "EKS control plane communication"
  vpc_id      = aws_vpc.this.id

  tags = {
    Name = "${local.cluster_name}-cluster"
  }
}

resource "aws_security_group" "nodes" {
  name_prefix = "${local.cluster_name}-nodes-"
  description = "EKS worker node and pod communication"
  vpc_id      = aws_vpc.this.id

  tags = {
    Name = "${local.cluster_name}-nodes"
  }
}

resource "aws_security_group_rule" "cluster_ingress_nodes_https" {
  type                     = "ingress"
  description              = "Worker nodes reach the Kubernetes API"
  security_group_id        = aws_security_group.cluster.id
  source_security_group_id = aws_security_group.nodes.id
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
}

resource "aws_security_group_rule" "nodes_ingress_cluster_ephemeral" {
  type                     = "ingress"
  description              = "Control plane reaches kubelet and node services"
  security_group_id        = aws_security_group.nodes.id
  source_security_group_id = aws_security_group.cluster.id
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
}

resource "aws_security_group_rule" "nodes_ingress_self" {
  type              = "ingress"
  description       = "Node and pod traffic inside the node group"
  security_group_id = aws_security_group.nodes.id
  self              = true
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
}
