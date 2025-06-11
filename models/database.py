import asyncpg
import asyncio
from typing import Optional, Dict, List, Any
from keys import get_keys
from util import logger


class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.keys = get_keys()
    
    async def initialize(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.keys.db_host,
                port=self.keys.db_port,
                user=self.keys.db_user,
                password=self.keys.db_pass,
                database=self.keys.db_name,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute_query(self, query: str, *args, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        async with self.pool.acquire() as conn:
            if user_id:
                await conn.execute("SET app.current_user_id = $1", user_id)
            
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_command(self, command: str, *args, user_id: Optional[int] = None) -> str:
        """Execute an INSERT/UPDATE/DELETE command."""
        async with self.pool.acquire() as conn:
            if user_id:
                await conn.execute("SET app.current_user_id = $1", user_id)
            
            result = await conn.execute(command, *args)
            return result
    
    async def execute_transaction(self, commands: List[tuple], user_id: Optional[int] = None) -> bool:
        """Execute multiple commands in a transaction."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if user_id:
                    await conn.execute("SET app.current_user_id = $1", user_id)
                
                for command, args in commands:
                    await conn.execute(command, *args)
                return True


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> DatabaseManager:
    """Get the database manager instance."""
    if not db_manager.pool:
        await db_manager.initialize()
    return db_manager