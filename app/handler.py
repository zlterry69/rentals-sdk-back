"""
AWS Lambda handler for HogarPeru Rentals Backend
"""
import json
import logging
import os
from typing import Dict, Any
from mangum import Mangum
from app.main import app
from app.database import get_supabase

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Debug AWS credentials
aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID', 'NOT_SET')
aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', 'NOT_SET')
logger.info(f"DEBUG AWS_ACCESS_KEY_ID: {aws_access_key[:10] if aws_access_key != 'NOT_SET' and len(aws_access_key) > 10 else aws_access_key}")
logger.info(f"DEBUG AWS_SECRET_ACCESS_KEY: {aws_secret_key[:10] if aws_secret_key != 'NOT_SET' and len(aws_secret_key) > 10 else aws_secret_key}")
logger.info(f"DEBUG AWS_ACCESS_KEY_ID length: {len(aws_access_key)}")
logger.info(f"DEBUG AWS_SECRET_ACCESS_KEY length: {len(aws_secret_key)}")

# Force Supabase initialization for Lambda
try:
    get_supabase()
    logger.info("Supabase client initialized in Lambda handler")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client in Lambda handler: {str(e)}")

# Create Mangum adapter for FastAPI
handler = Mangum(app, lifespan="off")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function
    """
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Process the request through Mangum
        response = handler(event, context)
        
        # Log the response for debugging
        logger.info(f"Response: {json.dumps(response)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }