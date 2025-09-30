"""
S3 Service for file management in HogarPeru
"""
import boto3
import os
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings
from app.utils.logging import get_request_logger
from app.utils.s3_folders import (
    generate_unique_filename,
    get_profile_image_key,
    get_property_image_key,
    get_invoice_key,
    get_contract_key,
    get_temp_upload_key,
    get_user_folder_prefix,
    get_property_folder_prefix,
    get_invoice_folder_prefix
)

logger = get_request_logger()

class S3Service:
    def __init__(self):
        """Initialize S3 client"""
        try:
            # En Lambda/EC2, boto3 usa IAM roles automáticamente
            # En desarrollo local, usa credenciales explícitas
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                # Desarrollo local con credenciales explícitas
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                logger.info("S3 service initialized with explicit credentials")
            else:
                # Producción (Lambda/EC2) con IAM roles
                self.s3_client = boto3.client(
                    's3',
                    region_name=settings.AWS_REGION
                )
                logger.info("S3 service initialized with IAM role")
            
            self.bucket_name = settings.S3_BUCKET_NAME
            logger.info(f"S3 bucket configured: {self.bucket_name}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 service: {str(e)}")
            self.s3_client = None

    def _check_client(self) -> bool:
        """Check if S3 client is available"""
        if not self.s3_client:
            logger.error("S3 client not available")
            return False
        return True

    async def upload_profile_image(self, user_id: str, file_content: bytes, 
                                 original_filename: str, content_type: str) -> Optional[str]:
        """
        Upload user profile image to S3
        
        Args:
            user_id: User ID
            file_content: File content as bytes
            original_filename: Original filename
            content_type: MIME type
            
        Returns:
            S3 URL if successful, None otherwise
        """
        if not self._check_client():
            return None
            
        try:
            # Generate unique filename
            unique_filename = generate_unique_filename(original_filename, "profile")
            
            # Generate S3 key
            s3_key = get_profile_image_key(user_id, unique_filename)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'user_id': user_id,
                    'upload_type': 'profile_image',
                    'original_filename': original_filename
                }
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"Profile image uploaded successfully for user {user_id}: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload profile image for user {user_id}: {str(e)}")
            return None

    async def upload_property_image(self, property_id: str, file_content: bytes,
                                  original_filename: str, content_type: str,
                                  image_type: str = "main") -> Optional[str]:
        """
        Upload property image to S3
        
        Args:
            property_id: Property ID
            file_content: File content as bytes
            original_filename: Original filename
            content_type: MIME type
            image_type: Type of image (main, bedroom, kitchen, etc.)
            
        Returns:
            S3 URL if successful, None otherwise
        """
        if not self._check_client():
            return None
            
        try:
            # Generate unique filename with image type prefix
            unique_filename = generate_unique_filename(original_filename, image_type)
            
            # Generate S3 key
            s3_key = get_property_image_key(property_id, unique_filename)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'property_id': property_id,
                    'upload_type': 'property_image',
                    'image_type': image_type,
                    'original_filename': original_filename
                }
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"Property image uploaded successfully for property {property_id}: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload property image for property {property_id}: {str(e)}")
            return None

    async def upload_invoice(self, user_id: str, booking_id: str, file_content: bytes,
                           content_type: str = "application/pdf") -> Optional[str]:
        """
        Upload invoice PDF to S3
        
        Args:
            user_id: User ID
            booking_id: Booking ID
            file_content: PDF content as bytes
            content_type: MIME type (default: application/pdf)
            
        Returns:
            S3 URL if successful, None otherwise
        """
        if not self._check_client():
            return None
            
        try:
            # Generate unique filename for invoice
            unique_filename = generate_unique_filename(f"invoice_{booking_id}.pdf", "invoice")
            
            # Generate S3 key
            s3_key = get_invoice_key(user_id, unique_filename)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'user_id': user_id,
                    'booking_id': booking_id,
                    'upload_type': 'invoice',
                    'document_type': 'invoice'
                }
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"Invoice uploaded successfully for booking {booking_id}: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload invoice for booking {booking_id}: {str(e)}")
            return None

    async def delete_user_files(self, user_id: str) -> bool:
        """
        Delete all files associated with a user (profile images, invoices)
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self._check_client():
            return False
            
        try:
            # Get all user-related prefixes
            prefixes_to_delete = [
                get_user_folder_prefix(user_id),
                get_invoice_folder_prefix(user_id)
            ]
            
            deleted_count = 0
            for prefix in prefixes_to_delete:
                # List objects with this prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                
                if 'Contents' in response:
                    # Delete objects
                    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                    
                    if objects_to_delete:
                        self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects_to_delete}
                        )
                        deleted_count += len(objects_to_delete)
            
            logger.info(f"Deleted {deleted_count} files for user {user_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete files for user {user_id}: {str(e)}")
            return False

    async def delete_property_files(self, property_id: str) -> bool:
        """
        Delete all files associated with a property
        
        Args:
            property_id: Property ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self._check_client():
            return False
            
        try:
            # Get property folder prefix
            prefix = get_property_folder_prefix(property_id)
            
            # List objects with this prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            deleted_count = 0
            if 'Contents' in response:
                # Delete objects
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                if objects_to_delete:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    deleted_count = len(objects_to_delete)
            
            logger.info(f"Deleted {deleted_count} files for property {property_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete files for property {property_id}: {str(e)}")
            return False

    async def get_file_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for file access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL if successful, None otherwise
        """
        if not self._check_client():
            return None
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
            return None

    async def upload_file_to_s3(self, file_content: bytes, s3_key: str, 
                               content_type: str, metadata: Dict[str, str] = None) -> Optional[str]:
        """
        Generic file upload to S3
        
        Args:
            file_content: File content as bytes
            s3_key: S3 object key
            content_type: MIME type
            metadata: Optional metadata dictionary
            
        Returns:
            S3 URL if successful, None otherwise
        """
        if not self._check_client():
            return None
            
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=metadata or {}
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"File uploaded successfully to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            return None

    def check_bucket_exists(self) -> bool:
        """
        Check if the S3 bucket exists
        
        Returns:
            True if bucket exists, False otherwise
        """
        if not self._check_client():
            return False
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False

# Global S3 service instance
s3_service = S3Service()

# Convenience function for external imports
async def upload_file_to_s3(file_content: bytes, s3_key: str, 
                           content_type: str, metadata: Dict[str, str] = None) -> Optional[str]:
    """Convenience function to upload file to S3"""
    return await s3_service.upload_file_to_s3(file_content, s3_key, content_type, metadata)
