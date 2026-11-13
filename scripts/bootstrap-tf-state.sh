#!/usr/bin/env bash
# Create the S3 bucket that stores the Terraform state of infra/terraform and
# infra/platform. Idempotent: safe to run again. The destroy script never
# deletes this bucket, so state history survives teardowns.
#
# Usage: AWS_REGION=us-east-1 scripts/bootstrap-tf-state.sh
# Optional: TF_STATE_BUCKET=<name> to choose the bucket name.
set -euo pipefail

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

REGION="${AWS_REGION:-us-east-1}"
PROJECT="${PROJECT_NAME:-app-nube-2}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${TF_STATE_BUCKET:-${PROJECT}-tfstate-${ACCOUNT}}"

if aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "==> Bucket $BUCKET already exists"
else
  echo "==> Creating bucket $BUCKET in $REGION"
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
  fi
fi

echo "==> Enabling versioning, encryption, and the public access block"
aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo
echo "State bucket ready. Use it with:"
echo "  export TF_STATE_BUCKET=$BUCKET"
echo "  export AWS_REGION=$REGION"
echo "and register TF_STATE_BUCKET as a GitHub Actions variable."
