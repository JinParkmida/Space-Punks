from typing import Optional, Dict, Any
from models.database import get_db
from util import logger


class Player:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.credits = 1000
        self.fuel = 100
        self.current_planet = 'Terra Prime'
        self.faction_id = None
        self.total_trades = 0
        self.successful_jumps = 0
        self.total_jumps = 0
        self.net_worth = 1000
    
    @classmethod
    async def get_or_create(cls, user_id: int, username: str) -> 'Player':
        """Get existing player or create new one."""
        db = await get_db()
        
        # Try to get existing player
        result = await db.execute_query(
            "SELECT * FROM players WHERE user_id = $1",
            user_id,
            user_id=user_id
        )
        
        if result:
            player_data = result[0]
            player = cls(user_id, username)
            player.credits = player_data['credits']
            player.fuel = player_data['fuel']
            player.current_planet = player_data['current_planet']
            player.faction_id = player_data['faction_id']
            player.total_trades = player_data['total_trades']
            player.successful_jumps = player_data['successful_jumps']
            player.total_jumps = player_data['total_jumps']
            player.net_worth = player_data['net_worth']
            return player
        
        # Create new player
        await db.execute_command(
            """INSERT INTO players (user_id, username) 
               VALUES ($1, $2)""",
            user_id, username,
            user_id=user_id
        )
        
        # Create ship for new player
        await db.execute_command(
            """INSERT INTO ships (user_id) VALUES ($1)""",
            user_id,
            user_id=user_id
        )
        
        logger.info(f"Created new player: {username} ({user_id})")
        return cls(user_id, username)
    
    async def save(self):
        """Save player data to database."""
        db = await get_db()
        await db.execute_command(
            """UPDATE players SET 
               credits = $2, fuel = $3, current_planet = $4, 
               faction_id = $5, total_trades = $6, successful_jumps = $7,
               total_jumps = $8, net_worth = $9, last_active = now()
               WHERE user_id = $1""",
            self.user_id, self.credits, self.fuel, self.current_planet,
            self.faction_id, self.total_trades, self.successful_jumps,
            self.total_jumps, self.net_worth,
            user_id=self.user_id
        )
    
    async def get_ship(self) -> Dict[str, Any]:
        """Get player's ship information."""
        db = await get_db()
        result = await db.execute_query(
            "SELECT * FROM ships WHERE user_id = $1",
            self.user_id,
            user_id=self.user_id
        )
        return result[0] if result else {}
    
    async def get_inventory(self) -> Dict[str, Dict[str, Any]]:
        """Get player's cargo inventory."""
        db = await get_db()
        result = await db.execute_query(
            "SELECT * FROM player_inventory WHERE user_id = $1",
            self.user_id,
            user_id=self.user_id
        )
        
        inventory = {}
        for item in result:
            inventory[item['commodity']] = {
                'quantity': item['quantity'],
                'average_buy_price': item['average_buy_price']
            }
        return inventory
    
    async def get_total_cargo(self) -> int:
        """Get total cargo currently held."""
        inventory = await self.get_inventory()
        return sum(item['quantity'] for item in inventory.values())
    
    async def calculate_net_worth(self) -> int:
        """Calculate player's total net worth including inventory."""
        inventory = await self.get_inventory()
        ship = await self.get_ship()
        
        # Get current market prices for inventory valuation
        db = await get_db()
        inventory_value = 0
        
        for commodity, data in inventory.items():
            if data['quantity'] > 0:
                price_result = await db.execute_query(
                    "SELECT current_price FROM market_prices WHERE planet = $1 AND commodity = $2",
                    self.current_planet, commodity
                )
                if price_result:
                    current_price = price_result[0]['current_price']
                    inventory_value += data['quantity'] * current_price
        
        ship_value = ship.get('total_upgrade_cost', 0)
        total_worth = self.credits + inventory_value + ship_value
        
        # Update net worth in database
        self.net_worth = total_worth
        await self.save()
        
        return total_worth
    
    async def add_achievement(self, achievement_id: int) -> bool:
        """Add achievement to player if not already unlocked."""
        db = await get_db()
        
        # Check if already unlocked
        existing = await db.execute_query(
            "SELECT 1 FROM player_achievements WHERE user_id = $1 AND achievement_id = $2",
            self.user_id, achievement_id,
            user_id=self.user_id
        )
        
        if existing:
            return False
        
        # Add achievement
        await db.execute_command(
            "INSERT INTO player_achievements (user_id, achievement_id) VALUES ($1, $2)",
            self.user_id, achievement_id,
            user_id=self.user_id
        )
        
        # Get achievement reward
        achievement = await db.execute_query(
            "SELECT reward_credits FROM achievements WHERE id = $1",
            achievement_id
        )
        
        if achievement and achievement[0]['reward_credits'] > 0:
            self.credits += achievement[0]['reward_credits']
            await self.save()
        
        return True
    
    async def check_achievements(self):
        """Check and unlock any new achievements."""
        db = await get_db()
        
        # Get all achievements not yet unlocked
        unlocked_achievements = await db.execute_query(
            """SELECT a.* FROM achievements a 
               WHERE a.id NOT IN (
                   SELECT achievement_id FROM player_achievements 
                   WHERE user_id = $1
               )""",
            self.user_id,
            user_id=self.user_id
        )
        
        for achievement in unlocked_achievements:
            requirement_met = False
            
            if achievement['requirement_type'] == 'trades':
                requirement_met = self.total_trades >= achievement['requirement_value']
            elif achievement['requirement_type'] == 'jumps':
                requirement_met = self.total_jumps >= achievement['requirement_value']
            elif achievement['requirement_type'] == 'credits':
                requirement_met = self.credits >= achievement['requirement_value']
            elif achievement['requirement_type'] == 'net_worth':
                await self.calculate_net_worth()
                requirement_met = self.net_worth >= achievement['requirement_value']
            elif achievement['requirement_type'] == 'faction_joined':
                requirement_met = self.faction_id is not None
            
            if requirement_met:
                await self.add_achievement(achievement['id'])
                logger.info(f"Player {self.username} unlocked achievement: {achievement['name']}")