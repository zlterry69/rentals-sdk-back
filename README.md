# RENTALS-BACK

Backend principal del sistema de alquileres (FastAPI + Supabase + AWS Lambda).

## Features
- CRUD de debtors, units, leases, payments
- Generación de recibos (PDF/PNG) y subida a S3
- Catálogos: currencies, process_status, banks
- Integración con microservicio de pagos (`RENTALS-SDK`)

## Tech stack
- FastAPI + Mangum
- PostgreSQL (Supabase)
- AWS Lambda + API Gateway
- S3 (recibos)
- GitHub Actions (CI/CD)

## Local development

### Prerequisites
- Python 3.11+
- Supabase project
- AWS CLI configured

### Setup
```bash
# Clone and setup
git clone <repo-url>
cd RENTALS-BACK

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env.local

# Edit .env.local with your values
```

### Environment variables (.env.local)
```bash
# Supabase
SUPABASE_DB_URL=postgresql://postgres:[password]@[host]:6543/postgres
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# AWS
S3_BUCKET=rentals-invoices-dev
AWS_REGION=us-east-1

# JWT
JWT_SECRET=your_jwt_secret_dev

# RENTALS-SDK
RENTALS_SDK_URL=http://localhost:8001
```

### Run locally
```bash
uvicorn app.main:app --reload --port 8000
```

### Database setup
```bash
# Run migrations automatically
python scripts/run_migrations.py

# Or run manually
cd database
psql $SUPABASE_DB_URL -f migrations/001_initial_schema.sql
psql $SUPABASE_DB_URL -f migrations/002_seed_data.sql
psql $SUPABASE_DB_URL -f migrations/003_add_invoices_table.sql
psql $SUPABASE_DB_URL -f migrations/004_seed_payment_methods.sql

# Check database connection
python scripts/run_migrations.py --check
```

## API Endpoints

### Health & Catalogs
- `GET /health` - Health check
- `GET /currencies` - List currencies
- `GET /process-status` - List process statuses
- `GET /banks` - List banks/providers

### Debtors
- `GET /debtors` - List debtors
- `POST /debtors` - Create debtor
- `GET /debtors/{public_id}` - Get debtor
- `PUT /debtors/{public_id}` - Update debtor
- `DELETE /debtors/{public_id}` - Delete debtor

### Units
- `GET /units` - List units
- `POST /units` - Create unit
- `GET /units/{public_id}` - Get unit
- `PUT /units/{public_id}` - Update unit
- `DELETE /units/{public_id}` - Delete unit

### Leases
- `GET /leases` - List leases
- `POST /leases` - Create lease
- `GET /leases/{public_id}` - Get lease
- `PUT /leases/{public_id}` - Update lease
- `DELETE /leases/{public_id}` - Delete lease

### Payments
- `GET /payments` - List payments
- `POST /payments` - Create payment (PENDING)
- `GET /payments/{public_id}` - Get payment with pre-signed URL
- `POST /payments/{public_id}/confirm` - Confirm payment
- `POST /payments/{public_id}/generate-receipt` - Generate receipt (PNG/PDF)

### Reports
- `GET /reports/payments` - Export payments (CSV/JSON)

### Invoices & Payment Methods
- `GET /invoices/payment-methods` - List payment methods
- `POST /invoices/payment-methods` - Create payment method
- `GET /invoices` - List invoices
- `GET /invoices/{public_id}` - Get invoice
- `POST /invoices` - Create invoice for payment
- `PUT /invoices/{public_id}` - Update invoice
- `POST /invoices/webhooks/{provider}` - Handle payment webhooks

## Deploy

### Branches → Environments
- `develop` → `dev`
- `release/*` → `cert`
- `main` → `prod`

### Manual deploy
```bash
# Deploy infrastructure
cd infra
npm install
npm run cdk deploy -- --profile your-aws-profile

# Deploy application
aws lambda update-function-code --function-name rentals-back-dev --zip-file fileb://app.zip
```

### CI/CD (GitHub Actions)
Automatically deploys on push to protected branches using OIDC authentication.

## Monitoring
- CloudWatch Logs
- API Gateway access logs
- Lambda Insights
- Alarms for errors → SNS notifications
- AWS Budgets alerts

## Cost optimization
- S3 lifecycle policies for old receipts
- Lambda provisioned concurrency (if needed)
- CloudWatch Insights for performance tuning
