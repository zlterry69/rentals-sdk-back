"""
AWS Lambda handler for HogarPeru Rentals Backend
"""
import json
import logging
from typing import Dict, Any
from mangum import Mangum
from app.main import app
from app.database import get_supabase

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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