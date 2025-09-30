"""
Payment Accounts management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger

logger = get_request_logger()
router = APIRouter()
security = HTTPBearer()

# Helper function for FastAPI dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extract user payload from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return payload

# Pydantic models
class PaymentAccountRequest(BaseModel):
    # Digital wallets
    yape_number: Optional[str] = None
    plin_number: Optional[str] = None
    
    # Cryptocurrency wallets
    bitcoin_wallet: Optional[str] = None
    ethereum_wallet: Optional[str] = None
    usdt_wallet: Optional[str] = None
    
    # Bank information
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    bank_holder_name: Optional[str] = None
    
    # Accepted payment methods
    accepts_yape: bool = False
    accepts_plin: bool = False
    accepts_bitcoin: bool = False
    accepts_ethereum: bool = False
    accepts_usdt: bool = False
    accepts_bank_transfer: bool = False
    accepts_mercadopago: bool = False
    accepts_izipay: bool = False

class PaymentAccountResponse(BaseModel):
    id: str
    public_id: str
    user_id: str
    yape_number: Optional[str] = None
    plin_number: Optional[str] = None
    bitcoin_wallet: Optional[str] = None
    ethereum_wallet: Optional[str] = None
    usdt_wallet: Optional[str] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None
    bank_holder_name: Optional[str] = None
    accepts_yape: bool = False
    accepts_plin: bool = False
    accepts_bitcoin: bool = False
    accepts_ethereum: bool = False
    accepts_usdt: bool = False
    accepts_bank_transfer: bool = False
    accepts_mercadopago: bool = False
    accepts_izipay: bool = False
    created_at: str
    updated_at: str

# Endpoints
@router.get("/", response_model=PaymentAccountResponse)
async def get_payment_account(
    current_user: dict = Depends(get_current_user)
):
    """Get current user's payment account information"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        result = supabase.table('user_payment_accounts').select('*').eq('user_id', user_id).execute()
        
        if not result.data:
            # Create default payment account if none exists
            from app.utils.id_generator import make_public_id
            account_data = {
                'public_id': make_public_id('upa'),
                'user_id': user_id,
                'accepts_yape': True,  # Enable at least one payment method by default
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            create_result = supabase.table('user_payment_accounts').insert(account_data).execute()
            if not create_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error creating payment account"
                )
            
            account = create_result.data[0]
        else:
            account = result.data[0]
        
        return PaymentAccountResponse(
            id=account['id'],
            public_id=account['public_id'],
            user_id=account['user_id'],
            yape_number=account.get('yape_number'),
            plin_number=account.get('plin_number'),
            bitcoin_wallet=account.get('bitcoin_wallet'),
            ethereum_wallet=account.get('ethereum_wallet'),
            usdt_wallet=account.get('usdt_wallet'),
            bank_account=account.get('bank_account'),
            bank_name=account.get('bank_name'),
            bank_holder_name=account.get('bank_holder_name'),
            accepts_yape=account.get('accepts_yape', False),
            accepts_plin=account.get('accepts_plin', False),
            accepts_bitcoin=account.get('accepts_bitcoin', False),
            accepts_ethereum=account.get('accepts_ethereum', False),
            accepts_usdt=account.get('accepts_usdt', False),
            accepts_bank_transfer=account.get('accepts_bank_transfer', False),
            accepts_mercadopago=account.get('accepts_mercadopago', False),
            accepts_izipay=account.get('accepts_izipay', False),
            created_at=account['created_at'],
            updated_at=account['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error fetching payment account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payment account"
        )

@router.put("/", response_model=PaymentAccountResponse)
async def update_payment_account(
    request: PaymentAccountRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's payment account information"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Check if payment account exists
        result = supabase.table('user_payment_accounts').select('id').eq('user_id', user_id).execute()
        
        if not result.data:
            # Create new payment account
            from app.utils.id_generator import make_public_id
            account_data = {
                'public_id': make_public_id('upa'),
                'user_id': user_id,
                'yape_number': request.yape_number,
                'plin_number': request.plin_number,
                'bitcoin_wallet': request.bitcoin_wallet,
                'ethereum_wallet': request.ethereum_wallet,
                'usdt_wallet': request.usdt_wallet,
                'bank_account': request.bank_account,
                'bank_name': request.bank_name,
                'bank_holder_name': request.bank_holder_name,
                'accepts_yape': request.accepts_yape or True,  # Ensure at least one is True
                'accepts_plin': request.accepts_plin,
                'accepts_bitcoin': request.accepts_bitcoin,
                'accepts_ethereum': request.accepts_ethereum,
                'accepts_usdt': request.accepts_usdt,
                'accepts_bank_transfer': request.accepts_bank_transfer,
                'accepts_mercadopago': request.accepts_mercadopago,
                'accepts_izipay': request.accepts_izipay,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            create_result = supabase.table('user_payment_accounts').insert(account_data).execute()
            if not create_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error creating payment account"
                )
            
            account = create_result.data[0]
        else:
            # Update existing payment account
            update_data = {
                'yape_number': request.yape_number,
                'plin_number': request.plin_number,
                'bitcoin_wallet': request.bitcoin_wallet,
                'ethereum_wallet': request.ethereum_wallet,
                'usdt_wallet': request.usdt_wallet,
                'bank_account': request.bank_account,
                'bank_name': request.bank_name,
                'bank_holder_name': request.bank_holder_name,
                'accepts_yape': request.accepts_yape,
                'accepts_plin': request.accepts_plin,
                'accepts_bitcoin': request.accepts_bitcoin,
                'accepts_ethereum': request.accepts_ethereum,
                'accepts_usdt': request.accepts_usdt,
                'accepts_bank_transfer': request.accepts_bank_transfer,
                'accepts_mercadopago': request.accepts_mercadopago,
                'accepts_izipay': request.accepts_izipay,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            update_result = supabase.table('user_payment_accounts').update(update_data).eq('user_id', user_id).execute()
            if not update_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error updating payment account"
                )
            
            account = update_result.data[0]
        
        return PaymentAccountResponse(
            id=account['id'],
            public_id=account['public_id'],
            user_id=account['user_id'],
            yape_number=account.get('yape_number'),
            plin_number=account.get('plin_number'),
            bitcoin_wallet=account.get('bitcoin_wallet'),
            ethereum_wallet=account.get('ethereum_wallet'),
            usdt_wallet=account.get('usdt_wallet'),
            bank_account=account.get('bank_account'),
            bank_name=account.get('bank_name'),
            bank_holder_name=account.get('bank_holder_name'),
            accepts_yape=account.get('accepts_yape', False),
            accepts_plin=account.get('accepts_plin', False),
            accepts_bitcoin=account.get('accepts_bitcoin', False),
            accepts_ethereum=account.get('accepts_ethereum', False),
            accepts_usdt=account.get('accepts_usdt', False),
            accepts_bank_transfer=account.get('accepts_bank_transfer', False),
            accepts_mercadopago=account.get('accepts_mercadopago', False),
            accepts_izipay=account.get('accepts_izipay', False),
            created_at=account['created_at'],
            updated_at=account['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error updating payment account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating payment account"
        )

@router.get("/public/{user_id}")
async def get_public_payment_methods(user_id: str):
    """Get public payment methods for a specific user (without sensitive info)"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('user_payment_accounts').select(
            'accepts_yape, accepts_plin, accepts_bitcoin, accepts_ethereum, accepts_usdt, accepts_bank_transfer, accepts_mercadopago, accepts_izipay'
        ).eq('user_id', user_id).execute()
        
        if not result.data:
            return {
                "accepts_yape": False,
                "accepts_plin": False,
                "accepts_bitcoin": False,
                "accepts_ethereum": False,
                "accepts_usdt": False,
                "accepts_bank_transfer": False,
                "accepts_mercadopago": False,
                "accepts_izipay": False
            }
        
        account = result.data[0]
        return {
            "accepts_yape": account.get('accepts_yape', False),
            "accepts_plin": account.get('accepts_plin', False),
            "accepts_bitcoin": account.get('accepts_bitcoin', False),
            "accepts_ethereum": account.get('accepts_ethereum', False),
            "accepts_usdt": account.get('accepts_usdt', False),
            "accepts_bank_transfer": account.get('accepts_bank_transfer', False),
            "accepts_mercadopago": account.get('accepts_mercadopago', False),
            "accepts_izipay": account.get('accepts_izipay', False)
        }
        
    except Exception as e:
        logger.error(f"Error fetching public payment methods: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching payment methods"
        )
