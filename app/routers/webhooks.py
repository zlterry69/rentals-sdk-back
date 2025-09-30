"""
Webhooks para recibir notificaciones de pagos externos
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from app.database import get_supabase
from app.utils.logging import get_request_logger

logger = get_request_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class PaymentWebhookRequest(BaseModel):
    order_id: str
    payment_id: str
    payment_status: str
    amount: float
    currency: str
    crypto_amount: Optional[float] = None
    crypto_currency: Optional[str] = None
    tx_hash: Optional[str] = None

@router.post("/nowpayments")
async def nowpayments_webhook(request: PaymentWebhookRequest, supabase = Depends(get_supabase)):
    """
    Webhook para recibir notificaciones de pagos de NOWPayments
    """
    try:
        logger.info(f"🔔 Webhook NOWPayments recibido: {request.order_id} - {request.payment_status}")
        
        # Extraer booking_id del order_id
        booking_public_id = None
        if request.order_id.startswith('ALQ-'):
            # Formato: ALQ-bkg_xxxx-timestamp o ALQ-unt_xxxx-timestamp
            parts = request.order_id.split('-')
            if len(parts) >= 2:
                # Si es bkg_xxxx, usarlo directamente
                if parts[1].startswith('bkg_'):
                    booking_public_id = parts[1]
                # Si es unt_xxxx, buscar la reserva más reciente para esa unidad
                elif parts[1].startswith('unt_'):
                    unit_public_id = parts[1]
                    # Buscar la reserva más reciente para esta unidad
                    booking_result = supabase.table('bookings').select('public_id').eq('units!unit_id.public_id', unit_public_id).order('created_at', desc=True).limit(1).execute()
                    if booking_result.data:
                        booking_public_id = booking_result.data[0]['public_id']
        elif request.order_id.startswith('bkg_'):
            # Formato: bkg_xxxx (direct booking public ID)
            booking_public_id = request.order_id
        
        logger.info(f"🔍 Extrayendo booking_public_id: order_id='{request.order_id}' -> booking_public_id='{booking_public_id}'")
        
        if not booking_public_id:
            logger.error(f"❌ Formato de order_id inválido: {request.order_id}")
            raise HTTPException(status_code=400, detail="Formato de order_id inválido")
        
        # Buscar la reserva en la base de datos
        booking_result = supabase.table('bookings').select('id, public_id, status_id').eq('public_id', booking_public_id).execute()
        
        if not booking_result.data:
            logger.error(f"❌ Reserva no encontrada: {booking_public_id}")
            raise HTTPException(status_code=404, detail="Reserva no encontrada")
        
        booking = booking_result.data[0]
        booking_id = booking['id']
        
        # Determinar el nuevo estado según el payment_status
        new_payment_status = "PENDING"
        new_booking_status = None
        
        if request.payment_status == "finished":
            new_payment_status = "PAID"
            # Buscar el status_id para BOOKING_CONFIRMED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CONFIRMED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"✅ Pago completado para reserva: {booking_public_id}")
            
        elif request.payment_status == "failed":
            new_payment_status = "FAILED"
            # Buscar el status_id para BOOKING_CANCELLED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CANCELLED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"❌ Pago falló para reserva: {booking_public_id}")
            
        elif request.payment_status == "confirming":
            new_payment_status = "CONFIRMING"
            logger.info(f"🔄 Pago confirmándose para reserva: {booking_public_id}")
            
        elif request.payment_status == "finished":
            new_payment_status = "PAID"
            # Buscar el status_id para BOOKING_CONFIRMED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CONFIRMED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"✅ Pago completado exitosamente para reserva: {booking_public_id}")
        
        # Actualizar la reserva en la base de datos
        update_data = {
            "payment_status": new_payment_status
        }
        
        # Si hay un nuevo estado de reserva, actualizarlo también
        if new_booking_status:
            update_data["status_id"] = new_booking_status
        
        # Actualizar la reserva
        update_result = supabase.table('bookings').update(update_data).eq('id', booking_id).execute()
        
        if update_result.data:
            logger.info(f"✅ Reserva actualizada exitosamente: {booking_public_id} -> {new_payment_status}")
            
            # Crear notificación para el usuario
            try:
                # Obtener información del usuario y la propiedad
                booking_details = supabase.table('bookings').select(
                    'guest_user_id, units!inner(title, owner_id)'
                ).eq('id', booking_id).execute()
                
                if booking_details.data:
                    booking_data = booking_details.data[0]
                    guest_id = booking_data['guest_user_id']
                    property_owner_id = booking_data['units']['owner_id']
                    property_title = booking_data['units']['title']
                    
                    # Crear notificación para el huésped
                    if request.payment_status == "finished":
                        notification_data = {
                            'public_id': f'not_{booking_public_id}_{request.payment_id}',
                            'user_id': guest_id,
                            'title': 'Pago completado exitosamente',
                            'message': f'Tu pago para {property_title} ha sido procesado correctamente',
                            'metadata': {
                                'booking_id': booking_public_id,
                                'payment_id': request.payment_id,
                                'amount': request.amount,
                                'currency': request.currency
                            },
                            'action_url': f'/bookings/{booking_public_id}',
                            'is_read': False
                        }
                        
                        # Buscar el tipo de notificación
                        type_result = supabase.table('notification_types').select('id').eq('code', 'payment_completed').execute()
                        if type_result.data:
                            notification_data['type_id'] = type_result.data[0]['id']
                        
                        supabase.table('notifications').insert(notification_data).execute()
                        logger.info(f"✅ Notificación creada para huésped: {guest_id}")
                    
            except Exception as notification_error:
                logger.error(f"⚠️ Error creando notificación: {str(notification_error)}")
            
            return {
                "status": "success", 
                "message": "Webhook procesado correctamente",
                "booking_public_id": booking_public_id,
                "new_payment_status": new_payment_status
            }
        else:
            logger.error(f"❌ Error actualizando reserva: {booking_public_id}")
            raise HTTPException(status_code=500, detail="Error actualizando reserva")
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook NOWPayments: {str(e)}")
        raise HTTPException(status_code=500, detail="Error procesando webhook")

@router.get("/test")
async def test_webhook():
    """
    Endpoint de prueba para verificar que los webhooks funcionan
    """
    return {"status": "success", "message": "Webhook endpoint funcionando"}
