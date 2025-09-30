import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, BinaryIO
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    """S3 service for file operations"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def put_object(
        self, 
        key: str, 
        data: BinaryIO, 
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Upload a file to S3
        
        Args:
            key: S3 object key
            data: File data (file-like object)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {
                'ContentType': content_type,
                'ACL': 'private'  # Private by default
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                data,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded successfully to S3: {key}")
            return True
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    def get_presigned_url(
        self, 
        key: str, 
        expiration: int = 3600,
        operation: str = "get_object"
    ) -> Optional[str]:
        """
        Generate a pre-signed URL for S3 object access
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            operation: S3 operation ('get_object', 'put_object', etc.)
        
        Returns:
            Pre-signed URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Pre-signed URL generated for: {key}")
            return url
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Error generating pre-signed URL: {e}")
            return None
    
    def delete_object(self, key: str) -> bool:
        """
        Delete an object from S3
        
        Args:
            key: S3 object key
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"File deleted from S3: {key}")
            return True
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3
        
        Args:
            key: S3 object key
        
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking object existence: {e}")
            return False
    
    def get_object_metadata(self, key: str) -> Optional[dict]:
        """
        Get object metadata from S3
        
        Args:
            key: S3 object key
        
        Returns:
            Metadata dictionary or None if error
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
            
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Error getting object metadata: {e}")
            return None

# Global S3 service instance
s3_service = S3Service()
