output "vpc_id" {
  description = "Identifier of the platform VPC."
  value       = aws_vpc.this.id
}

output "eks_cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "eks_cluster_certificate_authority_data" {
  description = "Base64 certificate authority data for the EKS cluster."
  value       = aws_eks_cluster.this.certificate_authority[0].data
  sensitive   = true
}

output "eks_node_group_name" {
  description = "EKS managed node group name."
  value       = aws_eks_node_group.this.node_group_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for the withdrawal-soles image."
  value       = aws_ecr_repository.withdrawal_soles.repository_url
}

output "rds_endpoint" {
  description = "PostgreSQL endpoint host and port."
  value       = aws_db_instance.this.endpoint
}

output "rds_database_name" {
  description = "PostgreSQL database name."
  value       = aws_db_instance.this.db_name
}

output "rds_port" {
  description = "PostgreSQL port."
  value       = aws_db_instance.this.port
}

output "configure_kubectl" {
  description = "Command that configures kubectl for the cluster."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.this.name}"
}
