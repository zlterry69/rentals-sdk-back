# Mapeo de Status - Inglés en BD, Español en Frontend

## Status de Deudores (debtors)

| Inglés (BD) | Español (Frontend) | Descripción |
|-------------|-------------------|-------------|
| `current` | Al Día | Deudor al día con los pagos |
| `overdue` | En Deuda | Deudor con pagos vencidos |
| `defaulted` | Moroso | Deudor con pagos muy atrasados |

## Status de Pagos (payments)

| Inglés (BD) | Español (Frontend) | Descripción |
|-------------|-------------------|-------------|
| `pending` | Pendiente | Pago pendiente de procesamiento |
| `paid` | Pagado | Pago completado exitosamente |
| `rejected` | Rechazado | Pago rechazado |
| `approved` | Aprobado | Pago aprobado por el propietario |

## Ventajas de usar Inglés en BD

1. **Consistencia**: Estándar internacional
2. **Mantenibilidad**: Más fácil para desarrolladores
3. **Escalabilidad**: Fácil integración con APIs externas
4. **Documentación**: Mejor para documentación técnica

## Implementación

- **Base de Datos**: Valores en inglés
- **Backend**: Maneja valores en inglés
- **Frontend**: Traduce a español para mostrar al usuario
- **APIs**: Devuelven valores en inglés, frontend los traduce
