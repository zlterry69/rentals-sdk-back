"""
Database connection and utilities for RENTALS-BACK using Supabase SDK
"""
import structlog
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from app.config import settings

logger = structlog.get_logger()

# Global Supabase client
_supabase_client: Optional[Client] = None


async def init_db():
    """Initialize Supabase client"""
    global _supabase_client
    
    try:
        # Create client with basic parameters (version 2.3.4 compatible)
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        logger.info("Supabase client created successfully")
        
        # Skip connection test for now to avoid startup issues
        # result = _supabase_client.table('currencies').select('count', count='exact').execute()
        # logger.info("Supabase connection test successful", count=result.count)
        
    except Exception as e:
        logger.error("Failed to initialize Supabase client", error=str(e))
        # Don't raise the error to allow the server to start
        logger.warning("Server will start without database connection")


async def close_db():
    """Close Supabase client (no-op for SDK)"""
    global _supabase_client
    if _supabase_client:
        _supabase_client = None
        logger.info("Supabase client closed")


def get_supabase() -> Client:
    """Get Supabase client"""
    if not _supabase_client:
        raise RuntimeError("Supabase client not initialized")
    return _supabase_client


class DatabaseService:
    """Service class for database operations"""
    
    @staticmethod
    async def execute_query(
        query: str, 
        params: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Any:
        """Execute a database query"""
        async with get_db_connection() as conn:
            if fetch_one:
                return await conn.fetchrow(query, *(params or ()))
            elif fetch_all:
                return await conn.fetch(query, *(params or ()))
            else:
                return await conn.execute(query, *(params or ()))
    
    @staticmethod
    async def execute_many(query: str, params_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets"""
        async with get_db_connection() as conn:
            await conn.executemany(query, params_list)
    
    @staticmethod
    async def fetch_one(query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch one row from database"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(query, *(params or ()))
            return dict(row) if row else None
    
    @staticmethod
    async def fetch_all(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows from database"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return [dict(row) for row in rows]
    
    @staticmethod
    async def fetch_paginated(
        query: str, 
        params: Optional[tuple] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """Fetch paginated results"""
        offset = (page - 1) * size
        
        # Count query
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subq"
        
        # Paginated query
        paginated_query = f"{query} LIMIT {size} OFFSET {offset}"
        
        async with get_db_connection() as conn:
            # Get total count
            count_row = await conn.fetchrow(count_query, *(params or ()))
            total = count_row['total'] if count_row else 0
            
            # Get paginated data
            rows = await conn.fetch(paginated_query, *(params or ()))
            data = [dict(row) for row in rows]
            
            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "pages": (total + size - 1) // size
                }
            }


# Convenience functions
async def execute_query(query: str, params: Optional[tuple] = None) -> str:
    """Execute a query and return status"""
    return await DatabaseService.execute_query(query, params)


async def fetch_one(query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    """Fetch one row"""
    return await DatabaseService.fetch_one(query, params)


async def fetch_all(query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Fetch all rows"""
    return await DatabaseService.fetch_all(query, params)


async def fetch_paginated(
    query: str, 
    params: Optional[tuple] = None,
    page: int = 1,
    size: int = 20
) -> Dict[str, Any]:
    """Fetch paginated results"""
    return await DatabaseService.fetch_paginated(query, params, page, size)
