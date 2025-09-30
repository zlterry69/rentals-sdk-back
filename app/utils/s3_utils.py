"""
S3 utilities for file uploads
"""
import boto3
import os
from datetime import datetime
from typing import Optional
from fastapi import UploadFile
import uuid
from botocore.exceptions import ClientError

def get_s3_client():
    """Get S3 client with credentials from environment"""
    from app.config import settings
    
    # Use settings from Pydantic configuration
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    region = settings.AWS_REGION
    
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables")
    
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )

def generate_s3_key(folder: str, filename: str) -> str:
    """Generate S3 key for file upload"""
    # Generate unique filename to avoid conflicts while preserving extension
    file_name, file_extension = os.path.splitext(filename)
    unique_filename = f"{file_name}_{uuid.uuid4()}{file_extension}"
    return f"{folder}/{unique_filename}"

def upload_to_s3(file: UploadFile, s3_key: str) -> str:
    """Upload file to S3 and return public URL"""
    try:
        from app.config import settings
        s3_client = get_s3_client()
        bucket_name = settings.S3_BUCKET_NAME
        
        # Upload file
        s3_client.upload_fileobj(
            file.file,
            bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': file.content_type
                # Sin ACL - el bucket ya tiene política pública
            }
        )
        
        # Generate public URL
        public_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
        return public_url
        
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise e

def delete_from_s3(s3_key: str) -> bool:
    """Delete file from S3"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        return True
        
    except Exception as e:
        print(f"Error deleting from S3: {e}")
        return False

def get_property_image_key(property_id: str, filename: str) -> str:
    """Generate S3 key for property images"""
    return generate_s3_key(f"properties/images/{property_id}", filename)

def get_user_profile_key(user_id: str, filename: str) -> str:
    """Generate S3 key for user profile images"""
    return generate_s3_key(f"users/profiles/{user_id}", filename)

def get_invoice_key(invoice_id: str, filename: str) -> str:
    """Generate S3 key for invoice documents"""
    return generate_s3_key(f"documents/invoices/{invoice_id}", filename)

def download_from_s3(s3_key: str, local_path: str) -> bool:
    """Download file from S3 to local path"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        s3_client.download_file(bucket_name, s3_key, local_path)
        return True
        
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return False

def copy_s3_object(source_key: str, dest_key: str) -> bool:
    """Copy object within S3 bucket"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        copy_source = {'Bucket': bucket_name, 'Key': source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket_name,
            Key=dest_key
        )
        return True
        
    except Exception as e:
        print(f"Error copying S3 object: {e}")
        return False

def get_s3_object_url(s3_key: str) -> str:
    """Get public URL for S3 object"""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
    region = os.getenv('AWS_REGION', 'us-east-1')
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"

def check_s3_object_exists(s3_key: str) -> bool:
    """Check if S3 object exists"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise e
    except Exception as e:
        print(f"Error checking S3 object: {e}")
        return False

def list_s3_objects(prefix: str = "", max_keys: int = 1000) -> list:
    """List objects in S3 bucket with optional prefix"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        return response.get('Contents', [])
        
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return []

def get_s3_object_metadata(s3_key: str) -> dict:
    """Get metadata for S3 object"""
    try:
        s3_client = get_s3_client()
        bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
        
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        return {
            'size': response.get('ContentLength', 0),
            'last_modified': response.get('LastModified'),
            'content_type': response.get('ContentType', ''),
            'etag': response.get('ETag', ''),
            'metadata': response.get('Metadata', {})
        }
        
    except Exception as e:
        print(f"Error getting S3 object metadata: {e}")
        return {}
