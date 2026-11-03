#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"
PLATFORM_DIR="$ROOT/infra/platform"
REGION="${AWS_REGION:-us-east-1}"

for command in terraform aws docker; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required for the EKS demo" >&2
    exit 1
  fi
done

cd "$ROOT"

CLUSTER="$(terraform -chdir="$TF_DIR" output -raw eks_cluster_name)"
ECR="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
DB_PASSWORD="$(sed -n 's/^db_password *= *"\(.*\)"/\1/p' "$TF_DIR/terraform.tfvars")"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "db_password not found in $TF_DIR/terraform.tfvars" >&2
  exit 1
fi

echo "==> Building and pushing image to ECR"
TAG="$(git rev-parse --short HEAD)"
IMAGE="$ECR:$TAG"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ECR%%/*}" >/dev/null
docker build -t "$IMAGE" "$ROOT"
docker push "$IMAGE" >/dev/null

echo "==> Applying the Terraform platform module"
terraform -chdir="$PLATFORM_DIR" init -backend=false -input=false >/dev/null
TF_VAR_db_password="$DB_PASSWORD" terraform -chdir="$PLATFORM_DIR" apply \
  -auto-approve -input=false -no-color \
  -var="image_tag=$TAG"

echo "==> Updating kubeconfig"
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER" >/dev/null

echo "==> Platform outputs"
terraform -chdir="$PLATFORM_DIR" output

echo "==> Cluster context"
echo "kubectl -n withdrawal-soles get pods,svc,ingress"
