#!/bin/bash

# HogarPeru Rentals Backend - AWS SAM Deployment Script
# Usage: ./deploy.sh [environment] [region]

set -e

# Default values
ENVIRONMENT=${1:-prod}
REGION=${2:-us-east-1}
STACK_NAME="rentals-backend-${ENVIRONMENT}"

echo "🚀 Deploying HogarPeru Rentals Backend to AWS Lambda"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Stack Name: ${STACK_NAME}"
echo "----------------------------------------"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in to AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Not logged in to AWS. Please run 'aws configure' first."
    exit 1
fi

# Build the application
echo "📦 Building the application..."
sam build --template-file template-simple.yaml

# Deploy the application
echo "🚀 Deploying to AWS..."
sam deploy \
    --template-file .aws-sam/build/template-simple.yaml \
    --stack-name ${STACK_NAME} \
    --s3-bucket sam-deployments-${ENVIRONMENT}-$(aws sts get-caller-identity --query Account --output text) \
    --s3-prefix rentals-backend \
    --region ${REGION} \
    --capabilities CAPABILITY_IAM

# Get the API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`RentalsBackendApi`].OutputValue' \
    --output text)

echo "✅ Deployment completed successfully!"
echo "🌐 API Gateway URL: ${API_URL}"
echo "📚 API Documentation: ${API_URL}/docs"

# Save the URL to a file for reference
echo "API_URL=${API_URL}" > .env.deployed
echo "ENVIRONMENT=${ENVIRONMENT}" >> .env.deployed
echo "REGION=${REGION}" >> .env.deployed

echo "💾 Configuration saved to .env.deployed"
