# Configuración del Sistema de Pagos

## Pasos para configurar el sistema de pagos

### 1. Crear las tablas en Supabase

Ejecuta el archivo SQL en el editor de Supabase:

```sql
-- Ejecutar create_payment_tables.sql en Supabase SQL Editor
```

### 2. Probar la creación de datos

```bash
cd RENTALS-BACK
python test_payment_creation.py
```

### 3. Probar el endpoint

```bash
# Primero obtén un token del frontend y configúralo en .env
# TEST_TOKEN=tu_token_aqui

python test_payments_endpoint.py
```

### 4. Estructura de las tablas creadas

#### Tabla `debtors` (Deudores/Inquilinos)
- `id`: UUID primario
- `public_id`: ID público único (deb_xxxxx)
- `full_name`: Nombre completo
- `email`: Email del inquilino
- `phone`: Teléfono
- `property_id`: Referencia a units(id)
- `monthly_rent`: Renta mensual
- `debt_amount`: Monto adeudado
- `status`: Estado (al_dia, en_deuda, moroso)
- `owner_id`: Referencia a users(id)

#### Tabla `payments` (Pagos)
- `id`: UUID primario
- `public_id`: ID público único (pay_xxxxx)
- `debtor_id`: Referencia a debtors(id)
- `amount`: Monto del pago
- `currency_id`: Referencia a currencies(id)
- `payment_method`: Método de pago
- `payment_origin`: Origen del pago (banco, etc.)
- `status`: Estado (pending, paid, rejected, approved)
- `description`: Descripción del pago
- `comments`: Comentarios
- `invoice_id`: ID de factura
- `receipt_url`: URL del recibo
- `receipt_s3_key`: Clave S3 del recibo

#### Tabla `payment_details` (Detalles del pago)
- `id`: UUID primario
- `payment_id`: Referencia a payments(id)
- `payment_origin`: Origen del pago
- `description`: Descripción
- `external_payment_id`: ID externo del pago
- `gateway_response`: Respuesta del gateway (JSON)

### 5. Endpoints disponibles

- `GET /payments/` - Obtener pagos del usuario
- `POST /payments/` - Crear nuevo pago
- `PATCH /payments/{payment_id}/approve` - Aprobar pago
- `PATCH /payments/{payment_id}/reject` - Rechazar pago
- `PATCH /payments/{payment_id}` - Actualizar pago

### 6. Próximos pasos

1. Ejecutar el SQL para crear las tablas
2. Probar la creación de datos
3. Probar el endpoint
4. Implementar pagos asíncronos con SDKs (NOWPayments, Izipay, MercadoPago)

### 7. Notas importantes

- Las tablas tienen RLS (Row Level Security) habilitado
- Los usuarios solo pueden ver sus propios pagos
- Se requiere autenticación para todos los endpoints
- Los archivos se suben a S3 automáticamente
