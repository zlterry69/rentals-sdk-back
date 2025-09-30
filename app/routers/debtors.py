from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import logging

from ..database import get_supabase
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.patch("/{debtor_id}/complete")
async def complete_rental(
    debtor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a rental as completed (tenant moved out and is up to date)"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub') or current_user.get('id')
        
        # Get debtor to verify ownership
        debtor_result = supabase.table('debtors').select('*').eq('id', debtor_id).eq('owner_id', user_id).execute()
        
        if not debtor_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debtor not found or access denied"
            )
        
        debtor = debtor_result.data[0]
        
        # Only mark as completed if debt_amount is 0
        if debtor.get('debt_amount', 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot mark as completed: debtor has outstanding debt"
            )
        
        # Update debtor status to completed
        update_result = supabase.table('debtors').update({
            'status': 'completed',
            'updated_at': datetime.now().isoformat()
        }).eq('id', debtor_id).execute()
        
        if not update_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update debtor status"
            )
        
        logger.info(f"Debtor {debtor_id} marked as completed by user {user_id}")
        
        return {
            "message": "Rental marked as completed",
            "debtor_id": debtor_id,
            "status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing rental for debtor {debtor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error completing rental"
        )

@router.get("/test")
async def test_debtors():
    """Test endpoint to check debtors without authentication"""
    try:
        supabase = get_supabase()
        
        # Get all debtors for testing
        result = supabase.table('debtors').select('''
            *,
            units!property_id(
                id,
                title,
                address,
                owner_id
            )
        ''').execute()
        
        if not result.data:
            return []
        
        # Format response
        debtors = []
        for debtor in result.data:
            unit = debtor.get('units', {})
            debtors.append({
                'id': debtor['id'],
                'public_id': debtor['public_id'],
                'full_name': debtor['full_name'],
                'email': debtor['email'],
                'phone': debtor.get('phone'),
                'property_id': debtor['property_id'],
                'property_name': unit.get('title', 'Propiedad no asignada'),
                'property_address': unit.get('address'),
                'monthly_rent': debtor.get('monthly_rent', 0),
                'debt_amount': debtor.get('debt_amount', 0),
                'status': debtor.get('status', 'current'),
                'created_at': debtor['created_at'],
                'updated_at': debtor['updated_at']
            })
        
        return debtors
        
    except Exception as e:
        logger.error(f"Error fetching debtors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching debtors"
        )

@router.post("/")
async def create_debtor(
    debtor_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new debtor (tenant)"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub') or current_user.get('id')
        
        # Validate user_id
        if not user_id or user_id == 'None':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Create debtor record
        debtor_record = {
            'public_id': f"deb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'full_name': debtor_data['full_name'],
            'email': debtor_data['email'],
            'phone': debtor_data.get('phone'),
            'property_id': debtor_data['property_id'],
            'monthly_rent': debtor_data['monthly_rent'],
            'debt_amount': 0,
            'status': 'current',
            'owner_id': user_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('debtors').insert(debtor_record).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create debtor"
            )
        
        logger.info(f"Created debtor {result.data[0]['public_id']} for user {user_id}")
        
        return {
            "message": "Debtor created successfully",
            "debtor": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating debtor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating debtor"
        )

@router.put("/{debtor_id}")
async def update_debtor(
    debtor_id: str,
    debtor_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a debtor"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub') or current_user.get('id')
        
        # Validate user_id
        if not user_id or user_id == 'None':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Verify debtor exists and belongs to user
        existing_debtor = supabase.table('debtors').select('id, owner_id').eq('public_id', debtor_id).eq('owner_id', user_id).execute()
        
        if not existing_debtor.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debtor not found or access denied"
            )
        
        # Update debtor
        update_data = {
            'name': debtor_data.get('full_name', ''),
            'full_name': debtor_data.get('full_name', ''),
            'email': debtor_data.get('email', ''),
            'phone': debtor_data.get('phone'),
            'property_id': debtor_data.get('property_id'),
            'monthly_rent': debtor_data.get('monthly_rent', 0),
            'status': debtor_data.get('status', 'current'),
            'updated_at': datetime.now().isoformat()
        }
        
        result = supabase.table('debtors').update(update_data).eq('public_id', debtor_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update debtor"
            )
        
        logger.info(f"Updated debtor {debtor_id} for user {user_id}")
        
        return {
            "message": "Debtor updated successfully",
            "debtor": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating debtor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating debtor"
        )

@router.delete("/{debtor_id}")
async def delete_debtor(
    debtor_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a debtor"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub') or current_user.get('id')
        
        # Validate user_id
        if not user_id or user_id == 'None':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Verify debtor exists and belongs to user
        existing_debtor = supabase.table('debtors').select('id, owner_id').eq('public_id', debtor_id).eq('owner_id', user_id).execute()
        
        if not existing_debtor.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debtor not found or access denied"
            )
        
        # Delete debtor
        result = supabase.table('debtors').delete().eq('public_id', debtor_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete debtor"
            )
        
        logger.info(f"Deleted debtor {debtor_id} for user {user_id}")
        
        return {
            "message": "Debtor deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting debtor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting debtor"
        )

@router.get("/")
async def get_debtors(
    current_user: dict = Depends(get_current_user)
):
    """Get all debtors for the current user"""
    try:
        supabase = get_supabase()
        # Try both 'sub' and 'id' fields
        user_id = current_user.get('sub') or current_user.get('id') or current_user.get('id')
        
        # Debug logging
        logger.info(f"Current user data: {current_user}")
        logger.info(f"User ID extracted: {user_id}")
        
        # Validate user_id
        if not user_id or user_id == 'None':
            logger.error(f"Invalid user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication"
            )
        
        # Get debtors with property information
        result = supabase.table('debtors').select('''
            *,
            units!property_id(
                id,
                title,
                address,
                owner_id
            )
        ''').eq('owner_id', user_id).execute()
        
        if not result.data:
            return []
        
        # Format response
        debtors = []
        for debtor in result.data:
            unit = debtor.get('units', {})
            debtors.append({
                'id': debtor['id'],
                'public_id': debtor['public_id'],
                'full_name': debtor['full_name'],
                'email': debtor['email'],
                'phone': debtor.get('phone'),
                'property_id': debtor['property_id'],
                'property_name': unit.get('title', 'Propiedad no asignada'),  # Cambiado de property_title a property_name
                'property_address': unit.get('address'),
                'monthly_rent': debtor.get('monthly_rent', 0),
                'debt_amount': debtor.get('debt_amount', 0),
                'status': debtor.get('status', 'current'),
                'created_at': debtor['created_at'],
                'updated_at': debtor['updated_at']
            })
        
        return debtors
        
    except Exception as e:
        logger.error(f"Error fetching debtors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching debtors"
        )