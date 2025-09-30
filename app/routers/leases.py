from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, date
import uuid
import logging
import json
from app.utils.auth import get_current_user
from app.services.s3_service import upload_file_to_s3
from app.utils.s3_folders import get_contract_key
from app.database import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def get_leases(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None
):
    """Get leases with pagination and filtering"""
    try:
        supabase = get_supabase()
        
        # Verificar si la tabla leases existe
        try:
            # Intentar hacer una consulta simple para verificar si la tabla existe
            test_query = supabase.table("leases").select("id").limit(1).execute()
        except Exception as table_error:
            logger.warning(f"Leases table does not exist or is not accessible: {str(table_error)}")
            # Devolver respuesta vacía si la tabla no existe
            return {
                "leases": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }
        
        offset = (page - 1) * limit
        
        # Debug: Log current user info
        logger.info(f"Current user ID: {current_user.get('id')}")
        logger.info(f"Current user data: {current_user}")
        
        # Construir query base
        query = supabase.table("leases").select("""
            *,
            units!unit_id(title, address, bedrooms, bathrooms, area_sqm, images),
            host:users!host_id(full_name, email),
            tenant:users!tenant_id(full_name, email, phone),
            currencies(code, name)
        """).eq("host_id", current_user["id"])
        
        if status:
            query = query.eq("status", status)
            
        # Aplicar paginación
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        leases = response.data
        logger.info(f"Found {len(leases)} leases for user {current_user.get('id')}")
        
        # Contar total
        count_query = supabase.table("leases").select("id", count="exact").eq("host_id", current_user["id"])
        if status:
            count_query = count_query.eq("status", status)
        
        count_response = count_query.execute()
        total = count_response.count or 0
        
        # Procesar datos
        leases_data = []
        for lease in leases:
            unit_data = lease.get("units", {})
            host_data = lease.get("host", {})
            tenant_data = lease.get("tenant", {})
            currency_data = lease.get("currencies", {})
            
            lease_dict = {
                "id": lease["id"],
                "public_id": lease["public_id"],
                "host_id": lease["host_id"],
                "tenant_id": lease["tenant_id"],
                "unit_id": lease["unit_id"],
                "start_date": lease["start_date"],
                "end_date": lease["end_date"],
                "contract_document_url": lease["contract_document_url"],
                "contract_document_s3_key": lease["contract_document_s3_key"],
                "rent_amount": lease.get("rent_amount", 0),
                "rent_frequency": lease.get("rent_frequency", "monthly"),
                "total_days": lease["total_days"],
                "total_amount": lease["total_amount"],
                "payment_method": lease.get("payment_method", "cash"),
                "status": lease["status"],
                "notes": lease["notes"],
                "expenses": lease.get("expenses", []),
                "created_at": lease["created_at"],
                "updated_at": lease["updated_at"],
                "property_title": unit_data.get("title") if unit_data else None,
                "property_address": unit_data.get("address") if unit_data else None,
                "bedrooms": unit_data.get("bedrooms") if unit_data else None,
                "bathrooms": unit_data.get("bathrooms") if unit_data else None,
                "area_sqm": unit_data.get("area_sqm") if unit_data else None,
                "property_images": unit_data.get("images") if unit_data else None,
                "tenant_name": tenant_data.get("full_name") if tenant_data else None,
                "tenant_email": tenant_data.get("email") if tenant_data else None,
                "tenant_phone": tenant_data.get("phone") if tenant_data else None,
                "host_name": host_data.get("full_name") if host_data else None,
                "host_email": host_data.get("email") if host_data else None,
                "currency_code": currency_data.get("code") if currency_data else None,
                "currency_name": currency_data.get("name") if currency_data else None
            }
            leases_data.append(lease_dict)
        
        return {
            "leases": leases_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching leases: {str(e)}")
        # Devolver respuesta vacía en caso de error
        return {
            "leases": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": 0,
                "pages": 0
            }
        }

@router.post("/")
async def create_lease(
    current_user: dict = Depends(get_current_user),
    unit_id: str = Form(...),
    tenant_id: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    rent_frequency: str = Form("monthly"),
    rent_amount: float = Form(...),
    payment_method: str = Form("cash"),
    notes: str = Form(""),
    expenses: str = Form("[]"),
    contract_document: Optional[UploadFile] = File(None)
):
    """Create a new lease"""
    try:
        logger.info(f"Creating lease with data: unit_id={unit_id}, tenant_id={tenant_id}, start_date={start_date}, end_date={end_date}")
        
        # Verificar que el usuario sea admin o superadmin
        user_role = current_user.get('role', 'user')
        logger.info(f"Current user role: {user_role}")
        logger.info(f"Current user data: {current_user}")
        
        if user_role not in ['admin', 'superadmin']:
            logger.warning(f"User {current_user.get('id')} with role '{user_role}' attempted to create lease")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden crear contratos"
            )
        
        supabase = get_supabase()
        
        # Generar public_id único
        public_id = str(uuid.uuid4())
        
        # Calcular total_days y total_amount
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end - start).days + 1  # +1 para incluir el día de inicio
        
        logger.info(f"Calculated: total_days={total_days}, rent_frequency={rent_frequency}, rent_amount={rent_amount}")
        
        # Calcular total_amount basado en frecuencia
        if rent_frequency == 'monthly':
            total_amount = rent_amount  # Usar monto mensual directamente
        elif rent_frequency == 'yearly':
            total_amount = rent_amount  # Usar monto anual directamente
        else:
            total_amount = rent_amount
            
        logger.info(f"Final total_amount={total_amount}")
        
        # Procesar archivo si se proporciona
        contract_document_url = None
        contract_document_s3_key = None
        
        if contract_document and contract_document.filename:
            try:
                logger.info(f"Processing contract document: {contract_document.filename}")
                # Leer contenido del archivo
                file_content = await contract_document.read()
                logger.info(f"File content size: {len(file_content)} bytes")
                
                # Subir archivo a S3
                s3_key = get_contract_key(public_id, contract_document.filename)
                logger.info(f"Uploading to S3 with key: {s3_key}")
                
                contract_document_url = await upload_file_to_s3(
                    file_content=file_content,
                    s3_key=s3_key,
                    content_type=contract_document.content_type or "application/octet-stream",
                    metadata={
                        'lease_id': public_id,
                        'upload_type': 'contract_document',
                        'original_filename': contract_document.filename
                    }
                )
                contract_document_s3_key = s3_key
                logger.info(f"File uploaded successfully. URL: {contract_document_url}")
            except Exception as e:
                logger.error(f"Error uploading contract document: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continuar sin el archivo si hay error
        
        # Procesar gastos
        import json
        expenses_data = json.loads(expenses) if expenses else []
        
        # Crear el contrato
        lease_data = {
            "public_id": public_id,
            "host_id": current_user["id"],
            "tenant_id": tenant_id,
            "unit_id": unit_id,
            "start_date": start_date,
            "end_date": end_date,
            "contract_document_url": contract_document_url,
            "contract_document_s3_key": contract_document_s3_key,
            "rent_amount": rent_amount,
            "rent_frequency": rent_frequency,
            "total_days": total_days,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "status": "active",
            "notes": notes,
            "expenses": expenses_data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"About to insert lease data: {lease_data}")
        
        response = supabase.table("leases").insert(lease_data).execute()
        
        logger.info(f"Insert response: {response}")
        
        if response.data:
            logger.info("Lease created successfully")
            return {"message": "Lease created successfully", "lease": response.data[0]}
        else:
            logger.error(f"Failed to create lease: {response}")
            raise HTTPException(status_code=400, detail="Failed to create lease")
            
    except Exception as e:
        import traceback
        logger.error(f"Error creating lease: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error creating lease: {str(e)}")

@router.get("/{lease_id}")
async def get_lease(
    lease_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific lease by ID"""
    try:
        supabase = get_supabase()
        
        response = supabase.table("leases").select("""
            *,
            units!unit_id(title, address, bedrooms, bathrooms, area_sqm, images),
            host:users!host_id(full_name, email),
            tenant:users!tenant_id(full_name, email, phone),
            currencies(code, name)
        """).eq("public_id", lease_id).eq("host_id", current_user["id"]).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Lease not found")
        
        lease = response.data[0]
        
        # Procesar datos
        unit_data = lease.get("units", {})
        host_data = lease.get("host", {})
        tenant_data = lease.get("tenant", {})
        currency_data = lease.get("currencies", {})
        
        lease_dict = {
            "id": lease["id"],
            "public_id": lease["public_id"],
            "host_id": lease["host_id"],
            "tenant_id": lease["tenant_id"],
            "unit_id": lease["unit_id"],
            "start_date": lease["start_date"],
            "end_date": lease["end_date"],
            "contract_document_url": lease["contract_document_url"],
            "contract_document_s3_key": lease["contract_document_s3_key"],
            "daily_rate": lease["daily_rate"],
            "total_days": lease["total_days"],
            "total_amount": lease["total_amount"],
            "deposit_amount": lease["deposit_amount"],
            "contract_type": lease["contract_type"],
            "status": lease["status"],
            "notes": lease["notes"],
            "renewal_date": lease["renewal_date"],
            "termination_date": lease["termination_date"],
            "termination_reason": lease["termination_reason"],
            "created_at": lease["created_at"],
            "updated_at": lease["updated_at"],
            "property_title": unit_data.get("title") if unit_data else None,
            "property_address": unit_data.get("address") if unit_data else None,
            "bedrooms": unit_data.get("bedrooms") if unit_data else None,
            "bathrooms": unit_data.get("bathrooms") if unit_data else None,
            "area_sqm": unit_data.get("area_sqm") if unit_data else None,
            "property_images": unit_data.get("images") if unit_data else None,
            "tenant_name": tenant_data.get("full_name") if tenant_data else None,
            "tenant_email": tenant_data.get("email") if tenant_data else None,
            "tenant_phone": tenant_data.get("phone") if tenant_data else None,
            "host_name": host_data.get("full_name") if host_data else None,
            "host_email": host_data.get("email") if host_data else None,
            "currency_code": currency_data.get("code") if currency_data else None,
            "currency_name": currency_data.get("name") if currency_data else None
        }
        
        return lease_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lease: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching lease")

@router.patch("/{lease_id}")
async def update_lease(
    lease_id: str,
    current_user: dict = Depends(get_current_user),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    daily_rate: Optional[float] = Form(None),
    deposit_amount: Optional[float] = Form(None),
    contract_type: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    renewal_date: Optional[str] = Form(None),
    termination_date: Optional[str] = Form(None),
    termination_reason: Optional[str] = Form(None),
    contract_document: Optional[UploadFile] = File(None)
):
    """Update a lease"""
    try:
        supabase = get_supabase()
        
        # Verificar que el contrato existe y pertenece al usuario
        existing_response = supabase.table("leases").select("id, public_id").eq("public_id", lease_id).eq("host_id", current_user["id"]).execute()
        
        if not existing_response.data:
            raise HTTPException(status_code=404, detail="Lease not found")
        
        existing_lease = existing_response.data[0]
        
        # Preparar datos de actualización
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if start_date is not None:
            update_data["start_date"] = start_date
        if end_date is not None:
            update_data["end_date"] = end_date
        if daily_rate is not None:
            update_data["daily_rate"] = daily_rate
        if deposit_amount is not None:
            update_data["deposit_amount"] = deposit_amount
        if contract_type is not None:
            update_data["contract_type"] = contract_type
        if status is not None:
            update_data["status"] = status
        if notes is not None:
            update_data["notes"] = notes
        if renewal_date is not None:
            update_data["renewal_date"] = renewal_date
        if termination_date is not None:
            update_data["termination_date"] = termination_date
        if termination_reason is not None:
            update_data["termination_reason"] = termination_reason
        
        # Recalcular total_days y total_amount si se actualizan fechas o daily_rate
        if start_date is not None or end_date is not None or daily_rate is not None:
            # Obtener datos actuales si no se proporcionan
            if start_date is None or end_date is None or daily_rate is None:
                current_response = supabase.table("leases").select("start_date, end_date, daily_rate").eq("public_id", lease_id).execute()
                if current_response.data:
                    current = current_response.data[0]
                    start_date = start_date or current["start_date"]
                    end_date = end_date or current["end_date"]
                    daily_rate = daily_rate or current["daily_rate"]
            
            if start_date and end_date and daily_rate:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                total_days = (end - start).days
                total_amount = daily_rate * total_days
                update_data["total_days"] = total_days
                update_data["total_amount"] = total_amount
        
        # Procesar archivo si se proporciona
        if contract_document and contract_document.filename:
            try:
                # Leer contenido del archivo
                file_content = await contract_document.read()
                
                # Subir archivo a S3
                s3_key = get_contract_key(existing_lease["public_id"], contract_document.filename)
                contract_document_url = await upload_file_to_s3(
                    file_content=file_content,
                    s3_key=s3_key,
                    content_type=contract_document.content_type or "application/octet-stream",
                    metadata={
                        'lease_id': existing_lease["public_id"],
                        'upload_type': 'contract_document',
                        'original_filename': contract_document.filename
                    }
                )
                update_data["contract_document_url"] = contract_document_url
                update_data["contract_document_s3_key"] = s3_key
            except Exception as e:
                logger.error(f"Error uploading contract document: {str(e)}")
                # Continuar sin actualizar el archivo si hay error
        
        # Actualizar el contrato
        response = supabase.table("leases").update(update_data).eq("public_id", lease_id).execute()
        
        if response.data:
            return {"message": "Lease updated successfully", "lease": response.data[0]}
        else:
            raise HTTPException(status_code=400, detail="Failed to update lease")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lease: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating lease")


@router.get("/{lease_id}/units")
async def get_host_units(
    current_user: dict = Depends(get_current_user)
):
    """Get units owned by the current user for lease creation"""
    try:
        supabase = get_supabase()
        
        response = supabase.table("units").select("id, public_id, title, address, bedrooms, bathrooms, area_sqm, images").eq("owner_id", current_user["id"]).execute()
        
        return {"units": response.data}
        
    except Exception as e:
        logger.error(f"Error fetching host units: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching host units")

@router.get("/{lease_id}/users")
async def get_tenant_users():
    """Get users with 'user' role for lease creation"""
    try:
        supabase = get_supabase()
        
        response = supabase.table("users").select("id, public_id, full_name, email, phone").eq("role", "user").execute()
        
        return {"users": response.data}
        
    except Exception as e:
        logger.error(f"Error fetching tenant users: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching tenant users")


@router.put("/{lease_id}")
async def update_lease(
    lease_id: str,
    unit_id: str = Form(...),
    tenant_id: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    rent_frequency: str = Form(...),
    rent_amount: float = Form(...),
    payment_method: str = Form(...),
    status: str = Form("active"),
    notes: str = Form(""),
    expenses: str = Form("[]"),
    current_user: dict = Depends(get_current_user)
):
    """Update a lease"""
    try:
        supabase = get_supabase()
        
        # Verificar que el usuario sea admin o superadmin
        user_role = current_user.get('role', 'user')
        user_id = current_user.get('id')
        
        if user_role not in ['admin', 'superadmin']:
            logger.warning(f"User {user_id} with role '{user_role}' attempted to update lease")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and superadmins can update leases"
            )
        
        # Verificar que el contrato existe
        lease_response = supabase.table("leases").select("*").eq("id", lease_id).execute()
        
        if not lease_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lease not found"
            )
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Calculate total days
        total_days = (end - start).days + 1
        
        # Calculate total amount
        total_amount = rent_amount
        
        # Parse expenses
        try:
            expenses_data = json.loads(expenses) if expenses else []
        except json.JSONDecodeError:
            expenses_data = []
        
        # Update lease data
        update_data = {
            "unit_id": unit_id,
            "tenant_id": tenant_id,
            "host_id": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "rent_frequency": rent_frequency,
            "rent_amount": rent_amount,
            "total_days": total_days,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "status": status,
            "notes": notes,
            "expenses": json.dumps(expenses_data),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update lease in database
        update_response = supabase.table("leases").update(update_data).eq("id", lease_id).execute()
        
        if update_response.data:
            logger.info(f"Lease {lease_id} updated successfully by user {user_id}")
            return {"message": "Lease updated successfully", "lease": update_response.data[0]}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update lease"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating lease: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error updating lease"
        )


@router.delete("/{lease_id}")
async def delete_lease(
    lease_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a lease"""
    try:
        logger.info(f"DELETE request received for lease_id: {lease_id}")
        supabase = get_supabase()
        
        # Verificar que el usuario sea admin o superadmin
        user_role = current_user.get('role', 'user')
        user_id = current_user.get('id')
        
        logger.info(f"User {user_id} with role '{user_role}' attempting to delete lease {lease_id}")
        
        if user_role not in ['admin', 'superadmin']:
            logger.warning(f"User {user_id} with role '{user_role}' attempted to delete lease")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and superadmins can delete leases"
            )
        
        # Verificar que el contrato existe
        logger.info(f"Searching for lease with public_id: {lease_id}")
        lease_response = supabase.table("leases").select("*").eq("public_id", lease_id).execute()
        
        logger.info(f"Lease search result: {len(lease_response.data) if lease_response.data else 0} leases found")
        
        if not lease_response.data:
            logger.warning(f"Lease {lease_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lease not found"
            )
        
        lease = lease_response.data[0]
        internal_id = lease["id"]  # Usar el ID interno para la eliminación
        
        logger.info(f"Found lease with internal_id: {internal_id}, attempting deletion")
        
        # Eliminar el contrato usando el ID interno
        delete_response = supabase.table("leases").delete().eq("id", internal_id).execute()
        
        logger.info(f"Delete response: {delete_response.data if delete_response.data else 'No data returned'}")
        
        if delete_response.data:
            logger.info(f"Lease {lease_id} deleted successfully by user {user_id}")
            return {"message": "Lease deleted successfully"}
        else:
            logger.error(f"Failed to delete lease {lease_id} - no data returned from delete operation")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete lease"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting lease: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting lease"
        )