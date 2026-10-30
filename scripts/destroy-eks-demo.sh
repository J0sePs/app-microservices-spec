#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"
REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="withdrawal-soles"

for command in terraform aws kubectl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required to destroy the EKS demo" >&2
    exit 1
  fi
done

if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "==> Removing namespace and LoadBalancer"
  kubectl delete namespace "$NAMESPACE" --wait=true --timeout=300s
fi

CLUSTER="$(terraform -chdir="$TF_DIR" output -raw eks_cluster_name 2>/dev/null || true)"
REPO="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url 2>/dev/null || true)"

if [ -n "$REPO" ]; then
  REPO_NAME="${REPO#*/}"
  IMAGE_IDS="$(aws ecr list-images --region "$REGION" --repository-name "$REPO_NAME" \
    --query 'imageIds' --output json 2>/dev/null || echo '[]')"
  if [ "$IMAGE_IDS" != "[]" ]; then
    echo "==> Deleting images from $REPO_NAME"
    aws ecr batch-delete-image --region "$REGION" --repository-name "$REPO_NAME" \
      --image-ids "$IMAGE_IDS" >/dev/null
  fi
fi

echo "==> Destroying Terraform resources"
terraform -chdir="$TF_DIR" destroy -auto-approve -input=false -no-color

if [ -n "$CLUSTER" ]; then
  echo "==> Deleting the EKS CloudWatch log group"
  aws logs delete-log-group --region "$REGION" \
    --log-group-name "/aws/eks/${CLUSTER}/cluster" 2>/dev/null || true
fi

echo "==> Terraform state"
terraform -chdir="$TF_DIR" state list
echo "Destroy complete. Verify AWS for any remaining billable resources."
