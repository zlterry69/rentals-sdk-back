import secrets
import string
from typing import Optional

def make_public_id(prefix: str, length: int = 12) -> str:
    """
    Generate a unique public ID following the convention: <prefijo>_<base62 10-14>
    
    Args:
        prefix: The prefix for the public ID (e.g., 'deb', 'pay', 'cur')
        length: The length of the random part (default: 12)
    
    Returns:
        A unique public ID string (e.g., 'deb_8fZk12Qp9L')
    
    Examples:
        >>> make_public_id('deb')
        'deb_8fZk12Qp9L'
        >>> make_public_id('pay', 14)
        'pay_8fZk12Qp9LmN2'
    """
    if not prefix or not prefix.strip():
        raise ValueError("Prefix cannot be empty")
    
    if length < 10 or length > 14:
        raise ValueError("Length must be between 10 and 14")
    
    # Base62 characters: 0-9, A-Z, a-z
    base62_chars = string.digits + string.ascii_uppercase + string.ascii_lowercase
    
    # Generate random string
    random_part = ''.join(secrets.choice(base62_chars) for _ in range(length))
    
    # Format: prefix_randompart
    return f"{prefix}_{random_part}"

def validate_public_id(public_id: str, expected_prefix: Optional[str] = None) -> bool:
    """
    Validate a public ID format
    
    Args:
        public_id: The public ID to validate
        expected_prefix: Optional expected prefix to check
    
    Returns:
        True if valid, False otherwise
    """
    if not public_id or '_' not in public_id:
        return False
    
    prefix, random_part = public_id.split('_', 1)
    
    # Check prefix if specified
    if expected_prefix and prefix != expected_prefix:
        return False
    
    # Check random part length
    if len(random_part) < 10 or len(random_part) > 14:
        return False
    
    # Check if random part contains only base62 characters
    base62_chars = string.digits + string.ascii_uppercase + string.ascii_lowercase
    if not all(c in base62_chars for c in random_part):
        return False
    
    return True

def extract_prefix(public_id: str) -> Optional[str]:
    """
    Extract the prefix from a public ID
    
    Args:
        public_id: The public ID
    
    Returns:
        The prefix or None if invalid
    """
    if not validate_public_id(public_id):
        return None
    
    return public_id.split('_')[0]
