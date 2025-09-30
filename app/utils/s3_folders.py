"""
S3 Bucket folder organization for HogarPeru
"""

# S3 Folder structure
S3_FOLDERS = {
    # User profile images
    'PROFILE_IMAGES': 'users/profiles/',
    
    # Property images
    'PROPERTY_IMAGES': 'properties/images/',
    'PROPERTY_THUMBNAILS': 'properties/thumbnails/',
    
    # Documents
    'INVOICES': 'documents/invoices/',
    'RECEIPTS': 'documents/receipts/',
    'CONTRACTS': 'documents/contracts/',
    
    # Temporary uploads
    'TEMP_UPLOADS': 'temp/',
}

def get_s3_key(folder_type: str, filename: str, user_id: str = None) -> str:
    """
    Generate S3 key for file upload
    
    Args:
        folder_type: Type of folder from S3_FOLDERS
        filename: Original filename
        user_id: User ID for user-specific files
    
    Returns:
        S3 key path
    """
    if folder_type not in S3_FOLDERS:
        raise ValueError(f"Invalid folder type: {folder_type}")
    
    base_path = S3_FOLDERS[folder_type]
    
    # Add user-specific subfolder for certain types
    if folder_type in ['PROFILE_IMAGES'] and user_id:
        base_path = f"{base_path}{user_id}/"
    
    return f"{base_path}{filename}"

def get_profile_image_key(user_id: str, filename: str) -> str:
    """Generate S3 key for user profile image"""
    unique_filename = generate_unique_filename(filename, "profile")
    return get_s3_key('PROFILE_IMAGES', unique_filename, user_id)

def get_property_image_key(property_id: str, filename: str) -> str:
    """Generate S3 key for property image"""
    unique_filename = generate_unique_filename(filename, "img")
    return f"{S3_FOLDERS['PROPERTY_IMAGES']}{property_id}/{unique_filename}"

def get_invoice_key(user_id: str, filename: str) -> str:
    """Generate S3 key for invoice document"""
    unique_filename = generate_unique_filename(filename, "invoice")
    return f"{S3_FOLDERS['INVOICES']}{user_id}/{unique_filename}"

def get_contract_key(lease_id: str, filename: str) -> str:
    """Generate S3 key for lease contract document"""
    unique_filename = generate_unique_filename(filename, "contract")
    return f"{S3_FOLDERS['CONTRACTS']}{lease_id}/{unique_filename}"

def get_temp_upload_key(filename: str) -> str:
    """Generate S3 key for temporary upload"""
    return f"{S3_FOLDERS['TEMP_UPLOADS']}{filename}"

def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate unique filename with timestamp and random string
    
    Args:
        original_filename: Original file name
        prefix: Optional prefix (e.g., 'profile', 'main', 'bedroom')
    
    Returns:
        Unique filename with format: prefix_YYYY_MM_DD_randomstring.ext
    """
    import uuid
    from datetime import datetime
    import os
    
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d")
    
    # Generate random string
    random_string = str(uuid.uuid4())[:8]
    
    # Combine parts
    if prefix:
        return f"{prefix}_{timestamp}_{random_string}{ext}"
    else:
        return f"{timestamp}_{random_string}{ext}"

def get_user_folder_prefix(user_id: str) -> str:
    """Get user folder prefix for S3 operations"""
    return f"users/profiles/{user_id}/"

def get_property_folder_prefix(property_id: str) -> str:
    """Get property folder prefix for S3 operations"""
    return f"properties/images/{property_id}/"

def get_invoice_folder_prefix(user_id: str) -> str:
    """Get invoice folder prefix for S3 operations"""
    return f"documents/invoices/{user_id}/"
