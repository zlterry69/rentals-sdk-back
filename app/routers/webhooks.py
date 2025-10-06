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
    # Campos adicionales de NOWPayments
    address: Optional[str] = None
    confirmations: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    actually_paid: Optional[float] = None
    order_description: Optional[str] = None
    purchase_id: Optional[str] = None
    outcome_amount: Optional[float] = None
    outcome_currency: Optional[str] = None
    pay_address: Optional[str] = None
    payin_extra_id: Optional[str] = None
    smart_contract: Optional[str] = None
    network: Optional[str] = None
    time_limit: Optional[str] = None
    burning_percent: Optional[float] = None
    expiration_estimate_date: Optional[str] = None
    is_fixed_rate: Optional[bool] = None
    is_fee_paid_by_merchant: Optional[bool] = None
    valid_until: Optional[str] = None
    type: Optional[str] = None

@router.post("/nowpayments")
async def nowpayments_webhook(request: PaymentWebhookRequest, supabase = Depends(get_supabase)):
    """
    Webhook para recibir notificaciones de pagos de NOWPayments
    """
    try:
        logger.info(f"🔔 Webhook NOWPayments recibido: {request.order_id} - {request.payment_status}")
        logger.info(f"🔍 Datos completos del webhook: {request.dict()}")
        logger.info(f"📦 Respuesta completa de NOWPayments que se guardará: {request.dict()}")
        
        # Detectar si es un pago DEMO
        if request.order_id.startswith('demo_'):
            logger.info(f"🎓 Pago DEMO detectado, order_id: {request.order_id}")
            
            # Crear registro del pago DEMO en la base de datos
            try:
                from datetime import datetime
                from app.utils.public_id import make_public_id
                
                # Obtener currency_id (default PEN)
                currency_result = supabase.table('currencies').select('id').eq('code', 'PEN').execute()
                currency_id = currency_result.data[0]['id'] if currency_result.data else None
                
                # Obtener status_id para PAID
                status_result = supabase.table('payment_status').select('id').eq('code', 'PAID').execute()
                paid_status_id = status_result.data[0]['id'] if status_result.data else None
                
                # Crear el registro del pago
                payment_data = {
                    'public_id': make_public_id('pay'),
                    'debtor_id': None,  # Sin debtor para pagos DEMO
                    'period': f"{datetime.now().year}-{datetime.now().month:02d}",
                    'amount': request.amount,
                    'currency_id': currency_id,
                    'method': 'crypto',
                    'payment_method': 'crypto',
                    'payment_origin': 'NOWPayments DEMO',
                    'status_id': paid_status_id,
                    'reference': f"demo_{request.payment_id}",
                    'invoice_id': f"demo_inv_{request.order_id}",
                    'description': f"Pago DEMO con {request.crypto_currency.upper() if request.crypto_currency else 'ETH'}",
                    'notes': f"DEMO - Payment ID: {request.payment_id} | Order ID: {request.order_id}",
                    'payment_date': datetime.now().isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                payment_result = supabase.table('payments').insert(payment_data).execute()
                logger.info(f"✅ Pago DEMO guardado en BD: {payment_result.data}")
                
                # Crear payment_details
                if payment_result.data:
                    payment_id = payment_result.data[0]['id']
                    details_data = {
                        'public_id': make_public_id('pdt'),
                        'payment_id': payment_id,
                        'payer_name': 'DEMO User',
                        'payer_email': 'demo@example.com',
                        'payment_method_code': 'crypto',
                        'payment_method_name': 'NOWPayments DEMO',
                        'sdk_response': request.dict(),
                        'transaction_id': request.payment_id,
                        'external_reference': request.order_id,
                        'comments': f"Pago DEMO procesado - {request.crypto_currency.upper() if request.crypto_currency else 'ETH'}: {request.crypto_amount}",
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    supabase.table('payment_details').insert(details_data).execute()
                    logger.info(f"✅ Payment details DEMO creado")
                
                return {
                    "status": "success",
                    "message": "Webhook DEMO procesado correctamente",
                    "order_id": request.order_id,
                    "payment_status": request.payment_status,
                    "payment_id": request.payment_id,
                    "is_demo": True
                }
            except Exception as demo_error:
                logger.error(f"❌ Error guardando pago DEMO: {str(demo_error)}")
                # Aún así retornar éxito para el simulador
                return {
                    "status": "success",
                    "message": "Webhook DEMO procesado (error al guardar en BD)",
                    "order_id": request.order_id,
                    "payment_status": request.payment_status,
                    "is_demo": True,
                    "error": str(demo_error)
                }
        
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
            
        elif request.payment_status == "cancelled":
            new_payment_status = "CANCELLED"
            # Buscar el status_id para BOOKING_CANCELLED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CANCELLED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"⏰ Pago cancelado por tiempo agotado para reserva: {booking_public_id}")
            logger.info(f"🔍 Status result para BOOKING_CANCELLED: {status_result.data}")
            logger.info(f"🔍 New booking status ID: {new_booking_status}")
            
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
            
            # Si el pago fue exitoso, crear un registro en la tabla payments
            if request.payment_status == "finished":
                try:
                    # Obtener información completa de la reserva
                    booking_details = supabase.table('bookings').select(
                        'guest_user_id, unit_id, total_amount, units!inner(title, owner_id)'
                    ).eq('id', booking_id).execute()
                    
                    if booking_details.data:
                        booking_data = booking_details.data[0]
                        guest_id = booking_data['guest_user_id']
                        unit_id = booking_data['unit_id']
                        total_amount = booking_data['total_amount']
                        property_title = booking_data['units']['title']
                        property_owner_id = booking_data['units']['owner_id']
                        
                        # Obtener información del usuario
                        user_result = supabase.table('users').select('full_name, email, phone').eq('id', guest_id).execute()
                        user_data = user_result.data[0] if user_result.data else {}
                        
                        # Importar funciones necesarias
                        from app.utils.id_generator import make_public_id
                        from datetime import datetime
                        
                        # Crear o encontrar debtor
                        debtor_result = supabase.table('debtors').select('id, public_id').eq('property_id', unit_id).eq('email', user_data.get('email', '')).execute()
                        
                        if debtor_result.data:
                            debtor_id = debtor_result.data[0]['id']
                        else:
                            # Crear nuevo debtor
                            debtor_public_id = make_public_id('deb')
                            debtor_data = {
                                'public_id': debtor_public_id,
                                'name': user_data.get('full_name', 'Unknown'),
                                'full_name': user_data.get('full_name', 'Unknown'),
                                'email': user_data.get('email', ''),
                                'phone': user_data.get('phone'),
                                'property_id': unit_id,
                                'monthly_rent': total_amount,
                                'debt_amount': 0,
                                'status': 'current',
                                'owner_id': property_owner_id,
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            debtor_result = supabase.table('debtors').insert(debtor_data).execute()
                            debtor_id = debtor_result.data[0]['id'] if debtor_result.data else None
                        
                        # También crear un debtor para el usuario que pagó (para que pueda ver su pago)
                        # Esto permite que el usuario vea sus propios pagos en /payments
                        user_debtor_result = supabase.table('debtors').select('id, public_id').eq('property_id', unit_id).eq('email', user_data.get('email', '')).eq('owner_id', guest_id).execute()
                        
                        if not user_debtor_result.data:
                            # Crear debtor para el usuario que pagó
                            user_debtor_public_id = make_public_id('deb')
                            user_debtor_data = {
                                'public_id': user_debtor_public_id,
                                'name': user_data.get('full_name', 'Unknown'),
                                'full_name': user_data.get('full_name', 'Unknown'),
                                'email': user_data.get('email', ''),
                                'phone': user_data.get('phone'),
                                'property_id': unit_id,
                                'monthly_rent': total_amount,
                                'debt_amount': 0,
                                'status': 'current',
                                'owner_id': guest_id,  # El usuario que pagó es el "owner" de este debtor
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            user_debtor_result = supabase.table('debtors').insert(user_debtor_data).execute()
                            user_debtor_id = user_debtor_result.data[0]['id'] if user_debtor_result.data else None
                        else:
                            user_debtor_id = user_debtor_result.data[0]['id']
                        
                        if debtor_id:
                            # Obtener currency_id para PEN
                            currency_result = supabase.table('currencies').select('id').eq('code', 'PEN').execute()
                            currency_id = currency_result.data[0]['id'] if currency_result.data else None
                            
                            # Obtener status_id para PAID
                            paid_status_result = supabase.table('process_status').select('id').eq('code', 'PAID').execute()
                            paid_status_id = paid_status_result.data[0]['id'] if paid_status_result.data else None
                            
                            # Crear registro de pago
                            from app.utils.id_generator import make_public_id
                            from datetime import datetime
                            
                            payment_data = {
                                'public_id': make_public_id('pay'),
                                'debtor_id': debtor_id,
                                'period': f"{datetime.now().year}-{datetime.now().month:02d}",
                                'amount': total_amount,
                                'currency_id': currency_id,
                                'method': 'crypto',
                                'payment_method': 'crypto',
                                'payment_origin': 'NOWPayments',
                                'status_id': paid_status_id,
                                'reference': f"nowpayments_{request.payment_id}",
                                'invoice_id': f"inv_{request.payment_id}",
                                'description': f"Pago con criptomonedas para {property_title}",
                                'notes': f"NOWPayments Payment ID: {request.payment_id}",
                                'payment_date': datetime.now().isoformat(),
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            payment_result = supabase.table('payments').insert(payment_data).execute()
                            
                            if payment_result.data:
                                payment_id = payment_result.data[0]['id']
                                
                                # Crear payment_details con la respuesta del SDK
                                details_data = {
                                    'public_id': make_public_id('pdt'),
                                    'payment_id': payment_id,
                                    'payer_name': user_data.get('full_name', 'Unknown'),
                                    'payer_email': user_data.get('email', ''),
                                    'payer_phone': user_data.get('phone'),
                                    'payment_method_code': 'crypto',
                                    'payment_method_name': 'NOWPayments',
                                    'sdk_response': request.dict(),
                                    'transaction_id': request.payment_id,
                                    'external_reference': request.order_id,
                                    'comments': f"Pago procesado por NOWPayments - {request.crypto_currency}",
                                    'created_by': property_owner_id,
                                    'created_at': datetime.now().isoformat(),
                                    'updated_at': datetime.now().isoformat()
                                }
                                
                                supabase.table('payment_details').insert(details_data).execute()
                                logger.info(f"✅ Registro de pago creado exitosamente: {payment_result.data[0]['public_id']}")
                                
                                # También crear un registro de pago para el usuario que pagó (para que pueda verlo en /payments)
                                if user_debtor_id:
                                    user_payment_data = {
                                        'public_id': make_public_id('pay'),
                                        'debtor_id': user_debtor_id,
                                        'period': f"{datetime.now().year}-{datetime.now().month:02d}",
                                        'amount': total_amount,
                                        'currency_id': currency_id,
                                        'method': 'crypto',
                                        'payment_method': 'crypto',
                                        'payment_origin': 'NOWPayments',
                                        'status_id': paid_status_id,
                                        'reference': f"nowpayments_{request.payment_id}",
                                        'invoice_id': f"inv_{request.payment_id}",
                                        'description': f"Pago con criptomonedas para {property_title}",
                                        'notes': f"NOWPayments Payment ID: {request.payment_id}",
                                        'payment_date': datetime.now().isoformat(),
                                        'created_at': datetime.now().isoformat(),
                                        'updated_at': datetime.now().isoformat()
                                    }
                                    
                                    user_payment_result = supabase.table('payments').insert(user_payment_data).execute()
                                    
                                    if user_payment_result.data:
                                        user_payment_id = user_payment_result.data[0]['id']
                                        
                                        # Crear payment_details para el usuario
                                        user_details_data = {
                                            'public_id': make_public_id('pdt'),
                                            'payment_id': user_payment_id,
                                            'payer_name': user_data.get('full_name', 'Unknown'),
                                            'payer_email': user_data.get('email', ''),
                                            'payer_phone': user_data.get('phone'),
                                            'payment_method_code': 'crypto',
                                            'payment_method_name': 'NOWPayments',
                                            'sdk_response': request.dict(),
                                            'transaction_id': request.payment_id,
                                            'external_reference': request.order_id,
                                            'comments': f"Pago procesado por NOWPayments - {request.crypto_currency}",
                                            'created_by': guest_id,  # El usuario que pagó
                                            'created_at': datetime.now().isoformat(),
                                            'updated_at': datetime.now().isoformat()
                                        }
                                        
                                        supabase.table('payment_details').insert(user_details_data).execute()
                                        logger.info(f"✅ Registro de pago para usuario creado exitosamente: {user_payment_result.data[0]['public_id']}")
                                    else:
                                        logger.error(f"❌ Error creando registro de pago para usuario: {booking_public_id}")
                            else:
                                logger.error(f"❌ Error creando registro de pago para reserva: {booking_public_id}")
                        
                except Exception as payment_error:
                    logger.error(f"❌ Error creando registro de pago: {str(payment_error)}")
                    # No fallar el webhook si no se puede crear el registro de pago
            
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

@router.post("/izipay")
async def izipay_webhook(request: dict, supabase = Depends(get_supabase)):
    """
    Webhook para recibir notificaciones de pagos de iZIPay
    """
    try:
        logger.info(f"🔔 Webhook iZIPay recibido: {request.get('order_id')} - {request.get('payment_status')}")
        logger.info(f"🔍 Datos completos del webhook: {request}")
        logger.info(f"📦 Respuesta completa de iZIPay que se guardará: {request}")

        # Extraer datos del request
        order_id = request.get('order_id')
        payment_id = request.get('payment_id')
        payment_status = request.get('payment_status')
        amount = request.get('amount')
        currency = request.get('currency')
        provider_tx = request.get('provider_tx')
        sdk_response = request.get('sdk_response', {})

        if not order_id or not payment_status:
            raise HTTPException(status_code=400, detail="order_id y payment_status son requeridos")

        # Buscar la reserva por order_id (asumiendo que order_id contiene el booking_public_id)
        booking_public_id = None
        if order_id.startswith('ALQ-'):
            # Formato: ALQ-bkg_xxxx-timestamp
            parts = order_id.split('-')
            if len(parts) >= 2:
                booking_public_id = parts[1]
        elif order_id.startswith('bkg_'):
            booking_public_id = order_id
        else:
            # Si no tiene formato conocido, usar el order_id directamente
            booking_public_id = order_id

        if not booking_public_id:
            logger.warning(f"⚠️ Formato de order_id desconocido: {order_id}")
            raise HTTPException(status_code=400, detail="Formato de order_id desconocido")

        # Buscar la reserva por public_id
        booking_result = supabase.table('bookings').select('id, public_id, status_id').eq('public_id', booking_public_id).execute()

        if not booking_result.data:
            logger.error(f"❌ Reserva no encontrada para public_id: {booking_public_id}")
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        booking_id = booking_result.data[0]['id']
        new_payment_status = None
        new_booking_status = None

        from app.utils.id_generator import make_public_id
        from datetime import datetime

        if payment_status == "finished":
            new_payment_status = "PAID"
            # Buscar el status_id para BOOKING_CONFIRMED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CONFIRMED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"✅ Pago completado para reserva: {booking_public_id}")

        elif payment_status == "failed":
            new_payment_status = "FAILED"
            # Buscar el status_id para BOOKING_CANCELLED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CANCELLED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"❌ Pago falló para reserva: {booking_public_id}")

        elif payment_status == "cancelled":
            new_payment_status = "CANCELLED"
            # Buscar el status_id para BOOKING_CANCELLED
            status_result = supabase.table('process_status').select('id').eq('code', 'BOOKING_CANCELLED').execute()
            if status_result.data:
                new_booking_status = status_result.data[0]['id']
            logger.info(f"⏰ Pago cancelado para reserva: {booking_public_id}")

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

            # Si el pago fue exitoso, crear un registro en la tabla payments
            if payment_status == "finished":
                try:
                    # Obtener información completa de la reserva
                    booking_details = supabase.table('bookings').select(
                        'guest_user_id, unit_id, total_amount, units!inner(title, owner_id)'
                    ).eq('id', booking_id).execute()

                    if booking_details.data:
                        booking_data = booking_details.data[0]
                        guest_id = booking_data['guest_user_id']
                        unit_id = booking_data['unit_id']
                        total_amount = booking_data['total_amount']
                        property_title = booking_data['units']['title']
                        property_owner_id = booking_data['units']['owner_id']

                        # Obtener información del usuario
                        user_result = supabase.table('users').select('full_name, email, phone').eq('id', guest_id).execute()
                        user_data = user_result.data[0] if user_result.data else {}

                        # Crear o encontrar debtor
                        debtor_result = supabase.table('debtors').select('id, public_id').eq('property_id', unit_id).eq('email', user_data.get('email', '')).execute()

                        if debtor_result.data:
                            debtor_id = debtor_result.data[0]['id']
                        else:
                            # Crear nuevo debtor
                            debtor_public_id = make_public_id('deb')
                            debtor_data = {
                                'public_id': debtor_public_id,
                                'name': user_data.get('full_name', 'Unknown'),
                                'full_name': user_data.get('full_name', 'Unknown'),
                                'email': user_data.get('email', ''),
                                'phone': user_data.get('phone'),
                                'property_id': unit_id,
                                'monthly_rent': total_amount,
                                'debt_amount': 0,
                                'status': 'current',
                                'owner_id': property_owner_id,
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }

                            debtor_result = supabase.table('debtors').insert(debtor_data).execute()
                            debtor_id = debtor_result.data[0]['id'] if debtor_result.data else None

                        # También crear un debtor para el usuario que pagó (para que pueda ver su pago)
                        user_debtor_result = supabase.table('debtors').select('id, public_id').eq('property_id', unit_id).eq('email', user_data.get('email', '')).eq('owner_id', guest_id).execute()

                        if not user_debtor_result.data:
                            # Crear debtor para el usuario que pagó
                            user_debtor_public_id = make_public_id('deb')
                            user_debtor_data = {
                                'public_id': user_debtor_public_id,
                                'name': user_data.get('full_name', 'Unknown'),
                                'full_name': user_data.get('full_name', 'Unknown'),
                                'email': user_data.get('email', ''),
                                'phone': user_data.get('phone'),
                                'property_id': unit_id,
                                'monthly_rent': total_amount,
                                'debt_amount': 0,
                                'status': 'current',
                                'owner_id': guest_id,  # El usuario que pagó es el "owner" de este debtor
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }

                            user_debtor_result = supabase.table('debtors').insert(user_debtor_data).execute()
                            user_debtor_id = user_debtor_result.data[0]['id'] if user_debtor_result.data else None
                        else:
                            user_debtor_id = user_debtor_result.data[0]['id']

                        if debtor_id:
                            # Obtener currency_id para PEN
                            currency_result = supabase.table('currencies').select('id').eq('code', 'PEN').execute()
                            currency_id = currency_result.data[0]['id'] if currency_result.data else None

                            # Obtener paid status_id
                            paid_status_result = supabase.table('process_status').select('id').eq('code', 'PAID').execute()
                            paid_status_id = paid_status_result.data[0]['id'] if paid_status_result.data else None

                            # Crear registro de pago para el propietario
                            payment_data = {
                                'public_id': make_public_id('pay'),
                                'debtor_id': debtor_id,
                                'amount': amount,
                                'currency_id': currency_id,
                                'method': 'card',
                                'payment_origin': 'iZIPay',
                                'status_id': paid_status_id,
                                'reference': f"izipay_{payment_id}",
                                'invoice_id': f"inv_{payment_id}",
                                'description': f"Pago con tarjeta para {property_title}",
                                'notes': f"iZIPay Order ID: {order_id}",
                                'period': f"{datetime.now().year}-{datetime.now().month:02d}",
                                'payment_date': datetime.now().isoformat(),
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }

                            payment_insert_result = supabase.table('payments').insert(payment_data).execute()

                            if payment_insert_result.data:
                                payment_id_db = payment_insert_result.data[0]['id']

                                # Crear payment_details para el propietario
                                details_data = {
                                    'public_id': make_public_id('pdt'),
                                    'payment_id': payment_id_db,
                                    'payer_name': user_data.get('full_name', 'Unknown'),
                                    'payer_email': user_data.get('email', ''),
                                    'payer_phone': user_data.get('phone'),
                                    'payment_method_code': 'card',
                                    'payment_method_name': 'iZIPay',
                                    'sdk_response': sdk_response,  # Respuesta completa del SDK de iZIPay
                                    'transaction_id': payment_id,
                                    'external_reference': order_id,
                                    'comments': f"Pago procesado por iZIPay - {currency}",
                                    'created_by': property_owner_id,
                                    'created_at': datetime.now().isoformat(),
                                    'updated_at': datetime.now().isoformat()
                                }

                                supabase.table('payment_details').insert(details_data).execute()
                                logger.info(f"✅ Registro de pago creado exitosamente: {payment_insert_result.data[0]['public_id']}")

                                # Crear registro de pago para el usuario que pagó (si es diferente al propietario)
                                if user_debtor_id and user_debtor_id != debtor_id:
                                    user_payment_data = {
                                        'public_id': make_public_id('pay'),
                                        'debtor_id': user_debtor_id,
                                        'amount': amount,
                                        'currency_id': currency_id,
                                        'method': 'card',
                                        'payment_origin': 'iZIPay',
                                        'status_id': paid_status_id,
                                        'reference': f"izipay_{payment_id}",
                                        'invoice_id': f"inv_{payment_id}",
                                        'description': f"Pago con tarjeta para {property_title}",
                                        'notes': f"iZIPay Order ID: {order_id}",
                                        'period': f"{datetime.now().year}-{datetime.now().month:02d}",
                                        'payment_date': datetime.now().isoformat(),
                                        'created_at': datetime.now().isoformat(),
                                        'updated_at': datetime.now().isoformat()
                                    }

                                    user_payment_result = supabase.table('payments').insert(user_payment_data).execute()

                                    if user_payment_result.data:
                                        user_payment_id = user_payment_result.data[0]['id']

                                        # Crear payment_details para el usuario
                                        user_details_data = {
                                            'public_id': make_public_id('pdt'),
                                            'payment_id': user_payment_id,
                                            'payer_name': user_data.get('full_name', 'Unknown'),
                                            'payer_email': user_data.get('email', ''),
                                            'payer_phone': user_data.get('phone'),
                                            'payment_method_code': 'card',
                                            'payment_method_name': 'iZIPay',
                                            'sdk_response': sdk_response,  # Respuesta completa del SDK de iZIPay
                                            'transaction_id': payment_id,
                                            'external_reference': order_id,
                                            'comments': f"Pago procesado por iZIPay - {currency}",
                                            'created_by': guest_id,  # El usuario que pagó
                                            'created_at': datetime.now().isoformat(),
                                            'updated_at': datetime.now().isoformat()
                                        }

                                        supabase.table('payment_details').insert(user_details_data).execute()
                                        logger.info(f"✅ Registro de pago para usuario creado exitosamente: {user_payment_result.data[0]['public_id']}")
                                    else:
                                        logger.error(f"❌ Error creando registro de pago para usuario: {booking_public_id}")
                            else:
                                logger.error(f"❌ Error creando registro de pago para reserva: {booking_public_id}")

                except Exception as payment_error:
                        logger.error(f"❌ Error creando registro de pago: {payment_error}")
                        # No levantar HTTPException aquí para no bloquear el webhook,
                        # pero registrar el error para depuración.

        return {"status": "success", "message": "Webhook iZIPay procesado correctamente", "booking_public_id": booking_public_id, "new_payment_status": new_payment_status}

    except HTTPException as e:
        logger.error(f"❌ Error en webhook iZIPay: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"❌ Error inesperado en webhook iZIPay: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar el webhook")

@router.get("/test")
async def test_webhook():
    """
    Endpoint de prueba para verificar que los webhooks funcionan
    """
    return {"status": "success", "message": "Webhook endpoint funcionando"}
