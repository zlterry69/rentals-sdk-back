"""
Payments management endpoints with detailed information
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import boto3
import os
import io
from app.config import settings
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger
from app.utils.id_generator import make_public_id

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
class PaymentDetailResponse(BaseModel):
    id: str
    public_id: str
    payment_id: str
    payer_name: Optional[str] = None
    payer_email: Optional[str] = None
    payer_phone: Optional[str] = None
    payer_document: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_email: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_account: Optional[str] = None
    payment_method_code: str
    payment_method_name: str
    sdk_response: Optional[dict] = None
    transaction_id: Optional[str] = None
    external_reference: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    cci: Optional[str] = None
    yape_plin_number: Optional[str] = None
    yape_plin_name: Optional[str] = None
    cash_receipt_number: Optional[str] = None
    cash_receipt_image_url: Optional[str] = None
    comments: Optional[str] = None
    internal_notes: Optional[str] = None
    created_at: str
    updated_at: str

class PaymentResponse(BaseModel):
    id: str
    public_id: str
    debtor_id: str
    debtor_name: str
    debtor_email: str
    debtor_phone: Optional[str] = None
    lease_id: str
    lease_title: Optional[str] = None
    period: str
    due_date: str
    paid_at: Optional[str] = None
    amount: float
    currency_id: str
    currency_code: str = "PEN"
    method: str
    reference: Optional[str] = None
    status_id: str
    status_name: str
    meter_start: Optional[float] = None
    meter_end: Optional[float] = None
    notes: Optional[str] = None
    s3_key: Optional[str] = None
    bank_id: Optional[str] = None
    invoice_id: Optional[str] = None
    created_at: str
    details: Optional[PaymentDetailResponse] = None

# Simple payment model for the frontend
class SimplePaymentResponse(BaseModel):
    id: str
    public_id: str
    debtor_name: str
    property_name: Optional[str] = None
    amount: float
    payment_date: str
    payment_method: str
    payment_origin: str
    status: str
    description: Optional[str] = None
    comments: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: str
    updated_at: str

# Models for creating payments
class PaymentCreate(BaseModel):
    debtor_id: str
    amount: float
    payment_method: str
    payment_origin: str
    description: Optional[str] = None
    comments: Optional[str] = None
    invoice_id: Optional[str] = None

class PaymentStatusUpdate(BaseModel):
    status: str

# S3 configuration
def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )

async def upload_to_s3(file: UploadFile, folder: str = "receipts") -> str:
    """Upload file to S3 and return the URL"""
    try:
        from app.services.s3_service import upload_file_to_s3
        from app.utils.s3_folders import get_s3_key, generate_unique_filename
        import uuid
        import os
        
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename using the same system as other uploads
        unique_filename = generate_unique_filename(file.filename, "receipt")
        
        # Generate S3 key using the same system as other uploads
        s3_key = get_s3_key('RECEIPTS', unique_filename)
        
        print(f"DEBUG S3 Key: {s3_key}")
        print(f"DEBUG File Info: {file.filename}, Content Type: {file.content_type}, Unique Filename: {unique_filename}")
        
        # Upload to S3 using the same service as other uploads
        file_url = await upload_file_to_s3(
            file_content=file_content,
            s3_key=s3_key,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                'upload_type': 'payment_receipt',
                'original_filename': file.filename
            }
        )
        
        if file_url:
            print(f"DEBUG S3 Upload Success: {file_url}")
            return file_url
        else:
            print("DEBUG S3 Upload Failed: upload_file_to_s3 returned None")
            return None
        
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        print(f"DEBUG S3 Error: {str(e)}")
        print(f"DEBUG S3 Error Type: {type(e).__name__}")
        # Return None instead of raising exception to allow payment creation without file
        return None

@router.post("/", response_model=SimplePaymentResponse)
async def create_payment(
    property_id: str = Form(...),
    user_id: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form(...),
    payment_origin: str = Form(...),
    description: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    invoice_id: Optional[str] = Form(None),
    receipt_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Create a new payment"""
    try:
        supabase = get_supabase()
        owner_id = current_user.get('sub')
        
        # Verify property exists and belongs to user
        property_result = supabase.table('units').select('id, title, owner_id').eq('public_id', property_id).execute()
        if not property_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        property_data = property_result.data[0]
        
        # Check if user owns this property (unless admin)
        if current_user.get('role') not in ['admin', 'superadmin']:
            if property_data['owner_id'] != owner_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this property"
                )
        
        # Verify user exists
        user_result = supabase.table('users').select('id, full_name, email, phone').eq('public_id', user_id).execute()
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = user_result.data[0]
        
        # Upload receipt if provided
        receipt_url = None
        if receipt_file:
            receipt_url = await upload_to_s3(receipt_file, "receipts")
            if receipt_url is None:
                logger.warning("File upload failed, but continuing with payment creation")
        
        # Get default currency (PEN)
        currency_result = supabase.table('currencies').select('id').eq('code', 'PEN').execute()
        currency_id = currency_result.data[0]['id'] if currency_result.data else None
        
        # Get pending status from process_status table
        status_result = supabase.table('process_status').select('id').eq('code', 'PENDING').execute()
        status_id = status_result.data[0]['id'] if status_result.data else None
        
        # Find or create debtor for this user-property combination
        debtor_result = supabase.table('debtors').select('id, public_id').eq('property_id', property_data['id']).eq('email', user_data['email']).execute()
        
        if debtor_result.data:
            debtor_id = debtor_result.data[0]['id']
            debtor_public_id = debtor_result.data[0]['public_id']
        else:
            # Create new debtor
            debtor_public_id = make_public_id('deb')
            debtor_data = {
                'public_id': debtor_public_id,
                'name': user_data['full_name'],
                'full_name': user_data['full_name'],
                'email': user_data['email'],
                'phone': user_data.get('phone'),
                'property_id': property_data['id'],
                'monthly_rent': 0,  # Will be updated when booking is confirmed
                'debt_amount': 0,
                'status': 'current',
                'owner_id': user_id
            }
            
            debtor_result = supabase.table('debtors').insert(debtor_data).execute()
            if not debtor_result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error creating debtor record"
                )
            debtor_id = debtor_result.data[0]['id']
        
        # Create payment
        period_value = f"{datetime.now().year}-{datetime.now().month:02d}"
        print(f"DEBUG Payment Period: {period_value}")
        
        payment_data = {
            'public_id': make_public_id('pay'),
            'debtor_id': debtor_id,
            'period': period_value,  # Required field: YYYY-MM format
            'amount': amount,
            'currency_id': currency_id,
            'method': payment_method,
            'payment_method': payment_method,
            'payment_origin': payment_origin,
            'status_id': status_id,
            'reference': invoice_id or f"inv_{make_public_id('inv')}",
            'invoice_id': invoice_id or f"inv_{make_public_id('inv')}",
            'description': description,
            'notes': comments,
            'comments': comments,
            's3_key': receipt_url,
            'receipt_url': receipt_url,
            'receipt_s3_key': receipt_url.split('/')[-1] if receipt_url else None,
            'payment_date': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        print(f"DEBUG Payment Data: {payment_data}")
        
        result = supabase.table('payments').insert(payment_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment"
            )
        
        payment = result.data[0]
        
        # Create payment details
        details_data = {
            'public_id': make_public_id('pdt'),
            'payment_id': payment['id'],
            'payer_name': user_data['full_name'],
            'payer_email': user_data['email'],
            'payer_phone': user_data.get('phone'),
            'payment_method_code': payment_method,
            'payment_method_name': payment_origin,
            'comments': description,
            'created_by': owner_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        supabase.table('payment_details').insert(details_data).execute()
        
        # Create or update debtor record for this user-property combination
        try:
            # Check if debtor already exists for this user-property combination
            existing_debtor = supabase.table('debtors').select('id, monthly_rent, debt_amount').eq('property_id', property_data['id']).eq('email', user_data['email']).eq('owner_id', owner_id).execute()
            
            if existing_debtor.data:
                # Update existing debtor
                debtor_update = {
                    'monthly_rent': property_data.get('monthly_rent', 0),
                    'debt_amount': max(0, existing_debtor.data[0].get('debt_amount', 0) - amount),  # Reduce debt
                    'status': 'current' if (existing_debtor.data[0].get('debt_amount', 0) - amount) <= 0 else 'overdue',
                    'name': user_data['full_name'],
                    'updated_at': datetime.now().isoformat()
                }
                
                update_result = supabase.table('debtors').update(debtor_update).eq('id', existing_debtor.data[0]['id']).execute()
                
                if update_result.data:
                    logger.info(f"Updated debtor record for payment {payment['public_id']}")
            else:
                # Create new debtor record
                debtor_data = {
                    'public_id': make_public_id('deb'),
                    'name': user_data['full_name'],
                    'full_name': user_data['full_name'],
                    'email': user_data['email'],
                    'phone': user_data.get('phone'),
                    'property_id': property_data['id'],
                    'monthly_rent': property_data.get('monthly_rent', 0),
                    'debt_amount': max(0, property_data.get('monthly_rent', 0) - amount),  # Calculate remaining debt
                    'status': 'current' if amount >= property_data.get('monthly_rent', 0) else 'overdue',
                    'owner_id': owner_id,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                debtor_result = supabase.table('debtors').insert(debtor_data).execute()
                
                if debtor_result.data:
                    logger.info(f"Created debtor record for payment {payment['public_id']}")
                    
        except Exception as e:
            logger.error(f"Error creating/updating debtor record for payment {payment['public_id']}: {str(e)}")
            # Don't fail the payment creation if debtor creation fails
        
        return SimplePaymentResponse(
            id=payment['id'],
            public_id=payment['public_id'],
            debtor_name=user_data['full_name'],
            property_name=property_data['title'],
            amount=float(payment['amount']),
            payment_date=payment['created_at'][:10],  # YYYY-MM-DD format
            payment_method=payment_method,
            payment_origin=payment_origin,
            status='pending',
            comments=comments,
            receipt_url=receipt_url,
            created_at=payment['created_at'],
            updated_at=payment['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating payment")

@router.patch("/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve a payment"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get payment details
        payment_result = supabase.table('payments').select(
            '*, debtors!inner(owner_id)'
        ).eq('public_id', payment_id).execute()
        
        if not payment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = payment_result.data[0]
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'superadmin']:
            if payment['debtors']['owner_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Get approved status ID - use PAID for approved payments
        status_result = supabase.table('process_status').select('id').eq('code', 'PAID').execute()
        if not status_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PAID status not found"
            )
        
        approved_status_id = status_result.data[0]['id']
        
        # Update payment status
        update_result = supabase.table('payments').update({
            'status_id': approved_status_id,
            'updated_at': datetime.now().isoformat()
        }).eq('public_id', payment_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to approve payment"
            )
        
        logger.info(f"Payment {payment_id} approved by user {user_id}")
        return {"message": "Payment approved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error approving payment")

@router.patch("/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject a payment"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get payment details
        payment_result = supabase.table('payments').select(
            '*, debtors!inner(owner_id)'
        ).eq('public_id', payment_id).execute()
        
        if not payment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = payment_result.data[0]
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'superadmin']:
            if payment['debtors']['owner_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Get rejected status ID - use FAILED for rejected payments
        status_result = supabase.table('process_status').select('id').eq('code', 'FAILED').execute()
        if not status_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FAILED status not found"
            )
        
        rejected_status_id = status_result.data[0]['id']
        
        # Update payment status
        update_result = supabase.table('payments').update({
            'status_id': rejected_status_id,
            'updated_at': datetime.now().isoformat()
        }).eq('public_id', payment_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reject payment"
            )
        
        logger.info(f"Payment {payment_id} rejected by user {user_id}")
        return {"message": "Payment rejected successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error rejecting payment")

@router.patch("/{payment_id}")
async def update_payment(
    payment_id: str,
    amount: Optional[float] = Form(None),
    payment_method: Optional[str] = Form(None),
    payment_origin: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    comments: Optional[str] = Form(None),
    invoice_id: Optional[str] = Form(None),
    receipt_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Update a payment"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get payment details
        payment_result = supabase.table('payments').select(
            '*, debtors!inner(owner_id)'
        ).eq('public_id', payment_id).execute()
        
        if not payment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = payment_result.data[0]
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'superadmin']:
            if payment['debtors']['owner_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Prepare update data
        update_data = {
            'updated_at': datetime.now().isoformat()
        }
        
        if amount is not None:
            update_data['amount'] = amount
        if payment_method is not None:
            update_data['method'] = payment_method
        if comments is not None:
            update_data['notes'] = comments
        if invoice_id is not None:
            update_data['reference'] = invoice_id
        
        # Upload new receipt if provided
        if receipt_file:
            receipt_url = upload_to_s3(receipt_file, "receipts")
            update_data['s3_key'] = receipt_url
        
        # Update payment
        update_result = supabase.table('payments').update(update_data).eq('public_id', payment_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update payment"
            )
        
        # Update payment details if provided
        if payment_origin is not None or description is not None:
            details_update = {}
            if payment_origin is not None:
                details_update['payment_method_name'] = payment_origin
            if description is not None:
                details_update['comments'] = description
            
            if details_update:
                details_update['updated_at'] = datetime.now().isoformat()
                supabase.table('payment_details').update(details_update).eq('payment_id', payment['id']).execute()
        
        logger.info(f"Payment {payment_id} updated by user {user_id}")
        return {"message": "Payment updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating payment")

@router.get("/", response_model=List[SimplePaymentResponse])
async def get_payments(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    debtor_id: Optional[str] = Query(None)
):
    """Get all payments with simplified information for the frontend"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build base query - using actual structure with status_id pointing to process_status
        query = supabase.table('payments').select('''
            *,
            debtors!inner(full_name, name, email, phone, property_id, owner_id),
            process_status!inner(code, description)
        ''')
        
        # Apply filters based on role and user type
        user_role = current_user.get('role', 'user')
        
        if user_role in ['admin', 'superadmin']:
            # Admins can see all payments (for support purposes)
            pass
        else:
            # Regular users: can see payments where they are either:
            # 1. The property owner (anfitrión) - to see payments from their tenants
            # 2. The debtor (inquilino) - to see their own payments
            
            # First, get units owned by the user (anfitrión)
            owned_units_result = supabase.table('units').select('id').eq('owner_id', user_id).execute()
            owned_unit_ids = [unit['id'] for unit in owned_units_result.data]
            
            # Get debtors where user is the tenant (inquilino)
            # In debtors table: owner_id = property owner, the debtor data is in name/full_name/email
            # We need to find debtors where the user's email matches the debtor's email
            user_debtor_ids = []
            try:
                # Get current user's email to match with debtors
                user_result = supabase.table('users').select('email').eq('id', user_id).execute()
                if user_result.data:
                    user_email = user_result.data[0]['email']
                    # Find debtors where the email matches the current user
                    user_debtors_result = supabase.table('debtors').select('id').eq('email', user_email).execute()
                    user_debtor_ids = [debtor['id'] for debtor in user_debtors_result.data]
            except Exception as e:
                logger.error(f"Error finding user debtors: {str(e)}")
                user_debtor_ids = []
            
            # Get debtors for properties owned by user (inquilinos del anfitrión)
            if owned_unit_ids:
                owner_debtors_result = supabase.table('debtors').select('id').in_('property_id', owned_unit_ids).execute()
                owner_debtor_ids = [debtor['id'] for debtor in owner_debtors_result.data]
            else:
                owner_debtor_ids = []
            
            # Combine all debtor IDs the user should see
            allowed_debtor_ids = user_debtor_ids + owner_debtor_ids
            
            if allowed_debtor_ids:
                query = query.in_('debtor_id', allowed_debtor_ids)
            else:
                # If user has no properties and is not a debtor, return empty
                # Use a UUID that doesn't exist to return empty results
                query = query.eq('debtor_id', '00000000-0000-0000-0000-000000000000')
        
        # Apply additional filters
        if status:
            query = query.eq('status', status)
        if method:
            query = query.eq('method', method)
        if debtor_id:
            query = query.eq('debtor_id', debtor_id)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        result = query.execute()
        
        payments = []
        for payment in result.data:
            # Get payment details for SDK response
            details_result = supabase.table('payment_details').select('*').eq('payment_id', payment['id']).execute()
            details = details_result.data[0] if details_result.data else None
            
            # Format payment date
            payment_date = payment.get('paid_at') or payment.get('created_at')
            if payment_date:
                try:
                    from datetime import datetime
                    if isinstance(payment_date, str):
                        payment_date = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
                    payment_date = payment_date.strftime('%Y-%m-%d')
                except:
                    payment_date = payment.get('created_at', '')
            
            # Get property name from debtors table
            property_name = None
            if payment.get('debtors') and payment['debtors'].get('property_id'):
                # Get property name from units table using property_id
                property_result = supabase.table('units').select('title').eq('id', payment['debtors']['property_id']).execute()
                if property_result.data:
                    property_name = property_result.data[0].get('title')
            
            # Get debtor name (check both full_name and name fields)
            debtor = payment.get('debtors', {})
            debtor_name = debtor.get('full_name') or debtor.get('name', 'Unknown')
            
            # Get status from process_status table
            process_status = payment.get('process_status', {})
            status = process_status.get('code', 'PENDING').lower() if process_status else 'pending'
            
            payment_response = SimplePaymentResponse(
                id=payment['id'],
                public_id=payment['public_id'],
                debtor_name=debtor_name,
                property_name=property_name,
                amount=float(payment['amount']),
                payment_date=payment_date,
                payment_method=payment.get('payment_method', 'Unknown'),
                payment_origin=payment.get('payment_origin', payment.get('payment_method', 'Unknown')),
                status=status,
                description=payment.get('description'),
                comments=payment.get('comments'),
                receipt_url=payment.get('receipt_url'),
                created_at=payment['created_at'],
                updated_at=payment.get('updated_at', payment['created_at'])
            )
            payments.append(payment_response)
        
        return payments
        
    except Exception as e:
        logger.error(f"Error fetching payments: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching payments")

@router.get("/{payment_id}/receipt")
async def download_receipt(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download payment receipt file"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get payment with debtor info to verify ownership
        payment_result = supabase.table('payments').select('''
            *,
            debtors!inner(owner_id)
        ''').eq('id', payment_id).eq('debtors.owner_id', user_id).execute()
        
        if not payment_result.data:
            raise HTTPException(status_code=404, detail="Payment not found or access denied")
        
        payment = payment_result.data[0]
        
        if not payment.get('receipt_url'):
            raise HTTPException(status_code=404, detail="No receipt available for this payment")
        
        receipt_url = payment['receipt_url']
        
        # If it's an S3 URL, generate a presigned URL for secure download
        if 's3' in receipt_url or 'amazonaws.com' in receipt_url:
            try:
                # Extract S3 key from URL
                if 'amazonaws.com' in receipt_url:
                    # Parse S3 URL to get bucket and key
                    parts = receipt_url.split('/')
                    bucket = parts[2].split('.')[0]
                    key = '/'.join(parts[3:])
                else:
                    # Assume it's already an S3 key
                    bucket = os.getenv('AWS_S3_BUCKET_NAME', 'hogarperu-receipts')
                    key = receipt_url
                
                # Generate presigned URL
                s3_client = get_s3_client()
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600  # 1 hour
                )
                
                # Redirect to presigned URL
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=presigned_url)
                
            except Exception as e:
                logger.error(f"Error generating presigned URL: {str(e)}")
                raise HTTPException(status_code=500, detail="Error accessing receipt file")
        
        else:
            # If it's a local file or other URL, return it directly
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=receipt_url)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading receipt: {str(e)}")
        raise HTTPException(status_code=500, detail="Error downloading receipt")

@router.get("/recent")
async def get_recent_payments(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Obtiene los pagos más recientes para el usuario actual
    """
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        logger.info(f"🔍 Getting recent payments for user: {user_id}")
        
        # Obtener pagos recientes del usuario
        # Primero obtener los IDs de las unidades que posee el usuario
        owned_units_result = supabase.table('units').select('id').eq('owner_id', user_id).execute()
        owned_unit_ids = [unit['id'] for unit in owned_units_result.data]
        logger.info(f"🏠 User owns {len(owned_unit_ids)} units: {owned_unit_ids}")
        
        if not owned_unit_ids:
            logger.info("⚠️ User has no units, returning empty payments")
            return {
                "payments": [],
                "total": 0,
                "limit": limit
            }
        
        # Obtener debtors para las unidades del usuario
        debtors_result = supabase.table('debtors').select('id, property_id, owner_id').in_('property_id', owned_unit_ids).execute()
        logger.info(f"👥 Found {len(debtors_result.data)} debtors for user's units")
        
        # También obtener debtors donde el usuario es el owner (pagos propios)
        user_debtors_result = supabase.table('debtors').select('id, property_id, owner_id').eq('owner_id', user_id).execute()
        logger.info(f"👤 Found {len(user_debtors_result.data)} debtors where user is owner")
        
        # Combinar ambos conjuntos de debtors
        all_debtor_ids = set()
        all_debtor_ids.update([debtor['id'] for debtor in debtors_result.data])
        all_debtor_ids.update([debtor['id'] for debtor in user_debtors_result.data])
        
        if not all_debtor_ids:
            logger.info("⚠️ No debtors found for user")
            return {
                "payments": [],
                "total": 0,
                "limit": limit
            }
        
        debtor_ids = list(all_debtor_ids)
        logger.info(f"🔗 Total unique debtor IDs: {len(debtor_ids)}")
        
        # Obtener pagos para estos debtors
        result = supabase.table('payments').select('''
            *,
            debtors!inner(full_name, name, email, phone, property_id, owner_id),
            process_status!inner(code, description),
            payment_details(sdk_response, payer_name, payer_email, payer_phone, payment_method_code, payment_method_name, transaction_id, external_reference, comments)
        ''').in_('debtor_id', debtor_ids).order('created_at', desc=True).limit(limit).execute()
        
        logger.info(f"💰 Found {len(result.data)} recent payments")
        
        return {
            "payments": result.data,
            "total": len(result.data),
            "limit": limit
        }
            
    except Exception as e:
        logger.error(f"Error fetching recent payments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching recent payments"
        )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific payment with detailed information"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get payment with related data
        result = supabase.table('payments').select('''
            *,
            debtors!inner(name, email, phone),
            leases!inner(unit_id, rent_amount, status, units!inner(title, address)),
            currencies!inner(code)
        ''').eq('public_id', payment_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = result.data[0]
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'superadmin']:
            # Regular users can only see their own payments
            if payment['debtors'].get('owner_id') != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Get payment details
        details_result = supabase.table('payment_details').select('*').eq('payment_id', payment['id']).execute()
        details = details_result.data[0] if details_result.data else None
        
        # Use status directly from payment
        status_name = payment.get('status', 'Unknown')
        
        return PaymentResponse(
            id=payment['id'],
            public_id=payment['public_id'],
            debtor_id=payment['debtor_id'],
            debtor_name=payment['debtors']['name'],
            debtor_email=payment['debtors']['email'],
            debtor_phone=payment['debtors'].get('phone'),
            lease_id=payment['lease_id'],
                lease_title=payment['leases']['units'].get('title'),
            period=payment['period'],
            due_date=payment['due_date'],
            paid_at=payment.get('paid_at'),
            amount=payment['amount'],
            currency_id=payment['currency_id'],
            currency_code=payment['currencies']['code'],
            method=payment['method'],
            reference=payment.get('reference'),
            status_id=payment['status_id'],
            status_name=status_name,
            meter_start=payment.get('meter_start'),
            meter_end=payment.get('meter_end'),
            notes=payment.get('notes'),
            s3_key=payment.get('s3_key'),
            bank_id=payment.get('bank_id'),
            invoice_id=payment.get('invoice_id'),
            created_at=payment['created_at'],
            details=PaymentDetailResponse(**details) if details else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment {payment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching payment")

@router.post("/{payment_id}/details")
async def create_payment_details(
    payment_id: str,
    details: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create payment details for a payment"""
    try:
        supabase = get_supabase()
        
        # Verify payment exists
        payment_result = supabase.table('payments').select('id').eq('public_id', payment_id).execute()
        if not payment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Create payment details
        details_data = {
            'public_id': make_public_id('pdt'),
            'payment_id': payment_result.data[0]['id'],
            'created_by': current_user.get('sub'),
            **details
        }
        
        result = supabase.table('payment_details').insert(details_data).execute()
        
        if result.data:
            return {"message": "Payment details created successfully", "details": result.data[0]}
        else:
            raise HTTPException(status_code=400, detail="Failed to create payment details")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment details: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating payment details")

@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a payment by ID"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # First, get the payment to check ownership
        payment_result = supabase.table('payments').select('''
            *,
            debtors!inner(owner_id, property_id)
        ''').eq('public_id', payment_id).execute()
        
        if not payment_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = payment_result.data[0]
        debtor = payment.get('debtors', {})
        
        # Check if user has permission to delete this payment
        # User can delete if:
        # 1. They are the property owner (debtor.owner_id == user_id)
        # 2. They are the debtor (payment is for their own booking)
        user_role = current_user.get('role', 'user')
        
        if user_role not in ['admin', 'superadmin']:
            # Get user's owned units
            owned_units_result = supabase.table('units').select('id').eq('owner_id', user_id).execute()
            owned_unit_ids = [unit['id'] for unit in owned_units_result.data]
            
            # Check if user owns the property or is the debtor
            can_delete = (
                debtor.get('owner_id') == user_id or  # User owns the property
                debtor.get('property_id') in owned_unit_ids  # User owns the unit
            )
            
            if not can_delete:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this payment"
                )
        
        # Delete the payment
        delete_result = supabase.table('payments').delete().eq('public_id', payment_id).execute()
        
        if not delete_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found or already deleted"
            )
        
        logger.info(f"Payment {payment_id} deleted successfully by user {user_id}")
        
        return {
            "message": "Payment deleted successfully",
            "payment_id": payment_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting payment"
        )
