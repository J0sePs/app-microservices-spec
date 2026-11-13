#!/usr/bin/env bash
# Create (or update) the least-privilege IAM user that GitHub Actions uses to
# publish images and apply infra/platform. Idempotent. Like the state bucket,
# the user lives outside Terraform so it survives stack teardowns.
#
# Usage:
#   scripts/bootstrap-ci-user.sh                 # user + inline policy only
#   scripts/bootstrap-ci-user.sh --create-key    # also create an access key and
#                                                # store it in GitHub secrets
#
# The access key goes straight from AWS into `gh secret set`; it is never
# printed or written to disk. After the user exists, add its ARN to
# cluster_admin_principal_arns in infra/terraform and apply, so it can reach
# the cluster API.
#
# Environment: AWS_REGION (default us-east-1), TF_STATE_BUCKET (required),
# CI_USER (default github-actions-withdrawal-soles), PROJECT_NAME, ENVIRONMENT.
set -euo pipefail

for command in aws gh; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required" >&2
    exit 1
  fi
done

REGION="${AWS_REGION:-us-east-1}"
CI_USER="${CI_USER:-github-actions-withdrawal-soles}"
PREFIX="${PROJECT_NAME:-app-nube-2}-${ENVIRONMENT:-dev}"
BUCKET="${TF_STATE_BUCKET:?Set TF_STATE_BUCKET (see scripts/bootstrap-tf-state.sh)}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
PARTITION="aws"

REPO_ARN="arn:${PARTITION}:ecr:${REGION}:${ACCOUNT}:repository/${PREFIX}/withdrawal-soles"
CLUSTER_ARN="arn:${PARTITION}:eks:${REGION}:${ACCOUNT}:cluster/${PREFIX}-eks"
BUCKET_ARN="arn:${PARTITION}:s3:::${BUCKET}"

POLICY="$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EcrLogin",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "EcrPushPull",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "${REPO_ARN}"
    },
    {
      "Sid": "EksDescribe",
      "Effect": "Allow",
      "Action": "eks:DescribeCluster",
      "Resource": "${CLUSTER_ARN}"
    },
    {
      "Sid": "StateList",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "${BUCKET_ARN}",
      "Condition": {
        "StringLike": {
          "s3:prefix": ["withdrawal-soles/*"]
        }
      }
    },
    {
      "Sid": "StateObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "${BUCKET_ARN}/withdrawal-soles/*"
    }
  ]
}
JSON
)"

if aws iam get-user --user-name "$CI_USER" >/dev/null 2>&1; then
  echo "==> IAM user $CI_USER already exists"
else
  echo "==> Creating IAM user $CI_USER"
  aws iam create-user --user-name "$CI_USER" \
    --tags "Key=Project,Value=${PROJECT_NAME:-app-nube-2}" "Key=Service,Value=withdrawal-soles" \
      "Key=Purpose,Value=github-actions" >/dev/null
fi

echo "==> Applying inline policy withdrawal-soles-ci"
aws iam put-user-policy --user-name "$CI_USER" \
  --policy-name withdrawal-soles-ci --policy-document "$POLICY"

USER_ARN="$(aws iam get-user --user-name "$CI_USER" --query User.Arn --output text)"
echo "    $USER_ARN"

if [[ "${1:-}" != "--create-key" ]]; then
  echo
  echo "Add the ARN to cluster_admin_principal_arns in infra/terraform and apply,"
  echo "then rerun with --create-key to store the access key in GitHub."
  exit 0
fi

KEY_COUNT="$(aws iam list-access-keys --user-name "$CI_USER" \
  --query 'length(AccessKeyMetadata)' --output text)"
if [[ "$KEY_COUNT" -ge 2 ]]; then
  echo "$CI_USER already has 2 access keys; delete one before creating another" >&2
  exit 1
fi

echo "==> Creating an access key and storing it in GitHub secrets"
read -r KEY_ID KEY_SECRET < <(aws iam create-access-key --user-name "$CI_USER" \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
printf '%s' "$KEY_ID" | gh secret set AWS_ACCESS_KEY_ID
printf '%s' "$KEY_SECRET" | gh secret set AWS_SECRET_ACCESS_KEY
printf '%s' "$REGION" | gh secret set AWS_REGION

echo "==> Waiting for the new key to propagate"
for _ in $(seq 1 12); do
  if AWS_ACCESS_KEY_ID="$KEY_ID" AWS_SECRET_ACCESS_KEY="$KEY_SECRET" \
      aws sts get-caller-identity >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo "==> Checking the key's permissions"
export AWS_ACCESS_KEY_ID="$KEY_ID" AWS_SECRET_ACCESS_KEY="$KEY_SECRET" AWS_REGION="$REGION"
unset AWS_PROFILE AWS_SESSION_TOKEN
aws sts get-caller-identity --query Arn --output text
aws s3api head-object --bucket "$BUCKET" --key withdrawal-soles/infra.tfstate >/dev/null \
  && echo "    S3 state: readable"
aws ecr describe-images --repository-name "${PREFIX}/withdrawal-soles" --max-items 1 >/dev/null \
  && echo "    ECR: readable"
aws eks describe-cluster --name "${PREFIX}-eks" --query cluster.status --output text \
  | sed 's/^/    EKS: /'
unset KEY_ID KEY_SECRET
echo "Done. Old keys (if any) can be deleted with aws iam delete-access-key."
