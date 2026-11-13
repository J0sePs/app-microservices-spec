#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"
PLATFORM_DIR="$ROOT/infra/platform"
REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="withdrawal-soles"

for command in terraform aws kubectl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required to destroy the EKS demo" >&2
    exit 1
  fi
done

DB_PASSWORD="$(sed -n 's/^db_password *= *"\(.*\)"/\1/p' "$TF_DIR/terraform.tfvars" 2>/dev/null || true)"
if [[ -z "$DB_PASSWORD" ]]; then
  echo "db_password not found in $TF_DIR/terraform.tfvars" >&2
  exit 1
fi

if [[ -z "${TF_STATE_BUCKET:-}" ]]; then
  echo "TF_STATE_BUCKET is not set; it must point at the state bucket" >&2
  exit 1
fi

export AWS_REGION="$REGION"
"$ROOT/scripts/tf-init.sh" terraform >/dev/null
"$ROOT/scripts/tf-init.sh" platform >/dev/null

echo "==> Destroying the platform module"
# jwt_secret has no default; destroy only needs a syntactically valid value.
TF_VAR_db_password="$DB_PASSWORD" \
TF_VAR_jwt_secret="${JWT_SECRET:-destroy-only-placeholder}" \
TF_VAR_state_bucket="$TF_STATE_BUCKET" \
TF_VAR_aws_region="$REGION" \
  terraform -chdir="$PLATFORM_DIR" destroy \
  -auto-approve -input=false -no-color

if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "==> Removing the remaining namespace and LoadBalancer"
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

echo "==> Destroying the infra module"
terraform -chdir="$TF_DIR" destroy -auto-approve -input=false -no-color

if [ -n "$CLUSTER" ]; then
  echo "==> Deleting the EKS CloudWatch log group"
  aws logs delete-log-group --region "$REGION" \
    --log-group-name "/aws/eks/${CLUSTER}/cluster" 2>/dev/null || true
fi

echo "==> Terraform states"
terraform -chdir="$PLATFORM_DIR" state list
terraform -chdir="$TF_DIR" state list
echo "Destroy complete. Verify AWS for any remaining billable resources."
echo "The state bucket s3://$TF_STATE_BUCKET is kept on purpose."
