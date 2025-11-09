#!/usr/bin/env bash
# Quick start local integration with LocalStack + Terraform + Docker services
# Usage: ./scripts/localstack-quickstart.sh

set -euo pipefail
cd "$(dirname "$(realpath "$0")")/.."

check_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Required command '$1' not found. Install it and retry."; exit 2; } }

check_cmd docker
check_cmd terraform
check_cmd aws

echo "1/5 Starting LocalStack..."
cd localstack
docker compose down -v || true
docker compose up -d
sleep 15

echo "2/5 Applying infra (terraform)..."
cd ../infra
rm -rf .terraform* terraform.tfstate* || true
terraform init -input=false
terraform apply -var-file=dev.tfvars -auto-approve

echo "3/5 Building and running order-api..."
cd ../order-api
docker build -t order-api .

SQS_QUEUE_URL=$(cd ../infra && terraform output -raw sqs_queue_url)
DDB_TABLE=$(cd ../infra && terraform output -raw dynamodb_table_name)
export AWS_ENDPOINT_URL="http://host.docker.internal:4566"

docker rm -f order-api 2>/dev/null || true
docker run -d --name order-api -p 8000:8000 \
  -e SQS_QUEUE_URL="$SQS_QUEUE_URL" \
  -e DDB_TABLE="$DDB_TABLE" \
  -e AWS_ENDPOINT_URL="$AWS_ENDPOINT_URL" \
  order-api

echo "4/5 Building and running order-processor..."
cd ../order-processor
go mod tidy
docker build --no-cache -t order-processor .

HOST_PORT=${HOST_PORT:-9091}
docker rm -f order-processor 2>/dev/null || true
docker run -d --name order-processor -p ${HOST_PORT}:9090 \
  -e SQS_QUEUE_URL="$SQS_QUEUE_URL" \
  -e DDB_TABLE="$DDB_TABLE" \
  -e AWS_ENDPOINT_URL="$AWS_ENDPOINT_URL" \
  order-processor

echo "Done. Services running:"
echo " - Order API: http://localhost:8000"
echo " - Processor metrics/health: http://localhost:${HOST_PORT}"
echo "Tip: run ./scripts/smoke.sh to verify end-to-end."