"""
Currency service that fetches currencies from each payment provider
"""
import httpx
import structlog
from typing import Dict, List, Any
from app.config import settings

logger = structlog.get_logger()


class CurrencyService:
    """Service to fetch currencies from payment providers"""
    
    async def get_available_currencies(self, provider: str) -> List[Dict[str, Any]]:
        """Get available currencies from specific provider"""
        
        if provider == "nowpayments":
            return await self._get_nowpayments_currencies()
        elif provider == "mercadopago":
            return await self._get_mercadopago_currencies()
        elif provider == "izipay":
            return await self._get_izipay_currencies()
        else:
            return []
    
    async def _get_nowpayments_currencies(self) -> List[Dict[str, Any]]:
        """Fetch currencies from NOWPayments API"""
        try:
            async with httpx.AsyncClient() as client:
                # Get available currencies
                response = await client.get(
                    "https://api.nowpayments.io/v1/currencies",
                    headers={"x-api-key": settings.NOWPAYMENTS_API_KEY}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    currencies = []
                    
                    for currency in data.get("currencies", []):
                        currencies.append({
                            "code": currency.upper(),
                            "name": f"{currency.upper()} (Crypto)",
                            "type": "crypto",
                            "provider": "nowpayments",
                            "decimals": 8,  # Default for crypto
                            "is_active": True
                        })
                    
                    return currencies
                    
        except Exception as e:
            logger.error("Error fetching NOWPayments currencies", error=str(e))
            
        # Fallback currencies
        return [
            {"code": "BTC", "name": "Bitcoin", "type": "crypto", "provider": "nowpayments", "decimals": 8},
            {"code": "ETH", "name": "Ethereum", "type": "crypto", "provider": "nowpayments", "decimals": 18},
            {"code": "USDT", "name": "Tether USD", "type": "crypto", "provider": "nowpayments", "decimals": 6},
            {"code": "USDC", "name": "USD Coin", "type": "crypto", "provider": "nowpayments", "decimals": 6},
        ]
    
    async def _get_mercadopago_currencies(self) -> List[Dict[str, Any]]:
        """Get MercadoPago supported currencies"""
        # MercadoPago mainly supports local currencies
        return [
            {"code": "PEN", "name": "Soles Peruanos", "type": "fiat", "provider": "mercadopago", "decimals": 2},
            {"code": "USD", "name": "US Dollar", "type": "fiat", "provider": "mercadopago", "decimals": 2},
            {"code": "ARS", "name": "Peso Argentino", "type": "fiat", "provider": "mercadopago", "decimals": 2},
        ]
    
    async def _get_izipay_currencies(self) -> List[Dict[str, Any]]:
        """Get Izipay supported currencies"""
        return [
            {"code": "PEN", "name": "Soles Peruanos", "type": "fiat", "provider": "izipay", "decimals": 2},
            {"code": "USD", "name": "US Dollar", "type": "fiat", "provider": "izipay", "decimals": 2},
        ]
    
    async def get_all_currencies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get currencies from all providers"""
        currencies = {}
        
        providers = ["nowpayments", "mercadopago", "izipay"]
        
        for provider in providers:
            currencies[provider] = await self.get_available_currencies(provider)
        
        return currencies
    
    async def sync_currencies_to_db(self):
        """Sync currencies from APIs to database"""
        from app.database import execute_query, fetch_one
        
        all_currencies = await self.get_all_currencies()
        
        for provider, currencies in all_currencies.items():
            for currency in currencies:
                # Check if currency exists
                existing = await fetch_one(
                    "SELECT id FROM currencies WHERE code = $1",
                    (currency["code"],)
                )
                
                if not existing:
                    # Insert new currency
                    from app.utils.id_generator import make_public_id
                    public_id = make_public_id("cur")
                    
                    await execute_query(
                        """
                        INSERT INTO currencies (public_id, code, name, decimals)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (code) DO NOTHING
                        """,
                        (public_id, currency["code"], currency["name"], currency["decimals"])
                    )
                    
                    logger.info("Currency synced", code=currency["code"], provider=provider)
