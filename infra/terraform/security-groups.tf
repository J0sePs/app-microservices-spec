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

resource "aws_security_group_rule" "cluster_egress_all" {
  type              = "egress"
  description       = "Control plane outbound traffic to nodes and AWS services"
  security_group_id = aws_security_group.cluster.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "nodes_egress_all" {
  type              = "egress"
  description       = "Nodes pull images and reach AWS APIs through the NAT gateway"
  security_group_id = aws_security_group.nodes.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
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

resource "aws_security_group_rule" "cluster_ingress_nat_https" {
  type              = "ingress"
  description       = "Nodes reach the public EKS endpoint through the NAT gateway"
  security_group_id = aws_security_group.cluster.id
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["${aws_eip.nat.public_ip}/32"]
}

resource "aws_security_group_rule" "eks_cluster_ingress_nodes_https" {
  type                     = "ingress"
  description              = "Worker nodes reach the EKS-managed cluster security group"
  security_group_id        = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
  source_security_group_id = aws_security_group.nodes.id
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
}

resource "aws_security_group_rule" "eks_cluster_ingress_nat_https" {
  type              = "ingress"
  description       = "Nodes reach the EKS-managed endpoint through the NAT gateway"
  security_group_id = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["${aws_eip.nat.public_ip}/32"]
}

resource "aws_security_group_rule" "nodes_ingress_eks_cluster_ephemeral" {
  type                     = "ingress"
  description              = "EKS-managed control plane reaches kubelet and node services"
  security_group_id        = aws_security_group.nodes.id
  source_security_group_id = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
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
