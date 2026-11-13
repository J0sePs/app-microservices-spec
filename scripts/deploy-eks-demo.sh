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

if [[ -z "${TF_STATE_BUCKET:-}" ]]; then
  echo "TF_STATE_BUCKET is not set. Create it with scripts/bootstrap-tf-state.sh" >&2
  exit 1
fi

# Shared service JWT secret; must equal JWT_SECRET in billetera-api.
if [[ -z "${JWT_SECRET:-}" ]]; then
  echo "JWT_SECRET is not set. Export the secret shared with billetera-api." >&2
  exit 1
fi

export AWS_REGION="$REGION"
"$ROOT/scripts/tf-init.sh" terraform >/dev/null
"$ROOT/scripts/tf-init.sh" platform >/dev/null

CLUSTER="$(terraform -chdir="$TF_DIR" output -raw eks_cluster_name)"
ECR="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
DB_PASSWORD="$(sed -n 's/^db_password *= *"\(.*\)"/\1/p' "$TF_DIR/terraform.tfvars")"

if [[ -z "$DB_PASSWORD" ]]; then
  echo "db_password not found in $TF_DIR/terraform.tfvars" >&2
  exit 1
fi

# Wallet target. By default the service calls billetera-api through cluster
# DNS (http://billetera-api.billetera.svc.cluster.local:3000).
#   WALLET_MOCK_ENABLED=1    route wallet calls to the in-cluster mock stub
#                            (adds the /v1/ gateway route); use it while
#                            billetera-api is not deployed.
#   WALLET_SERVICE_URL=<url> call another wallet base URL instead.
WALLET_ARGS=()
if [[ "${WALLET_MOCK_ENABLED:-0}" == "1" || "${WALLET_MOCK_ENABLED:-}" == "true" ]]; then
  WALLET_ARGS+=(-var="wallet_mock_enabled=true")
  echo "==> Wallet calls routed to the in-cluster mock stub"
elif [[ -n "${WALLET_SERVICE_URL:-}" ]]; then
  WALLET_ARGS+=(-var="wallet_service_url=$WALLET_SERVICE_URL")
  echo "==> Wallet service URL overridden to $WALLET_SERVICE_URL"
fi

echo "==> Building and pushing image to ECR"
TAG="$(git rev-parse --short HEAD)"
IMAGE="$ECR:$TAG"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ECR%%/*}" >/dev/null
docker build -t "$IMAGE" "$ROOT"
docker push "$IMAGE" >/dev/null

echo "==> Applying the Terraform platform module"
TF_VAR_db_password="$DB_PASSWORD" \
TF_VAR_jwt_secret="$JWT_SECRET" \
TF_VAR_state_bucket="$TF_STATE_BUCKET" \
TF_VAR_aws_region="$REGION" \
  terraform -chdir="$PLATFORM_DIR" apply \
  -auto-approve -input=false -no-color \
  -var="image_tag=$TAG" "${WALLET_ARGS[@]}"

echo "==> Updating kubeconfig"
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER" >/dev/null

echo "==> Platform outputs"
terraform -chdir="$PLATFORM_DIR" output

echo "==> Cluster context"
echo "kubectl -n withdrawal-soles get pods,svc,ingress"
