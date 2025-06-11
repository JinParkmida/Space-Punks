import disnake
from disnake.ext import commands
from typing import Optional
import random

from models.database import get_db
from models.player import Player
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="market", description="View market information")
    async def market_group(self, inter):
        pass

    @market_group.sub_command(name="scan", description="View current market prices across all planets")
    async def market_scan(self, inter: disnake.AppCmdInter):
        """Display market prices for all commodities across planets."""
        db = await get_db()
        
        # Get all market data
        market_data = await db.execute_query(
            """SELECT mp.planet, mp.commodity, mp.current_price, mp.supply_level, mp.demand_level,
                      c.base_price, p.danger_level
               FROM market_prices mp
               JOIN commodities c ON mp.commodity = c.name
               JOIN planets p ON mp.planet = p.name
               ORDER BY mp.planet, mp.commodity"""
        )
        
        embed = await create_bot_author_embed(
            title="🌌 Galactic Market Scanner",
            description="Real-time commodity prices across all planets",
            color=0x00ff88
        )
        
        # Group by planet
        planets = {}
        for row in market_data:
            planet = row['planet']
            if planet not in planets:
                planets[planet] = []
            planets[planet].append(row)
        
        for planet, commodities in planets.items():
            danger_emoji = "🟢" if commodities[0]['danger_level'] <= 2 else "🟡" if commodities[0]['danger_level'] <= 3 else "🔴"
            
            market_text = ""
            for commodity in commodities:
                price = commodity['current_price']
                base_price = commodity['base_price']
                supply = commodity['supply_level']
                demand = commodity['demand_level']
                
                # Price trend indicator
                if price > base_price * 1.1:
                    trend = "📈"
                elif price < base_price * 0.9:
                    trend = "📉"
                else:
                    trend = "➡️"
                
                market_text += f"{trend} **{commodity['commodity']}**: {price:,} cr (S:{supply} D:{demand})\n"
            
            embed.add_field(
                name=f"{danger_emoji} {planet}",
                value=market_text,
                inline=True
            )
        
        embed.set_footer(text="💡 Tip: Higher danger planets often have better prices!")
        await send_message(embed=embed, inter=inter)

    @market_group.sub_command(name="planet", description="View detailed market info for a specific planet")
    async def market_planet(
        self, 
        inter: disnake.AppCmdInter,
        planet: str = commands.Param(description="Planet name to check")
    ):
        """Display detailed market information for a specific planet."""
        db = await get_db()
        
        # Validate planet exists
        planet_data = await db.execute_query(
            "SELECT * FROM planets WHERE LOWER(name) = LOWER($1)",
            planet
        )
        
        if not planet_data:
            await send_message(
                msg="❌ Planet not found! Use `/market scan` to see all available planets.",
                inter=inter,
                ephemeral=True
            )
            return
        
        planet_info = planet_data[0]
        
        # Get market data for this planet
        market_data = await db.execute_query(
            """SELECT mp.*, c.description, c.base_price
               FROM market_prices mp
               JOIN commodities c ON mp.commodity = c.name
               WHERE mp.planet = $1
               ORDER BY mp.commodity""",
            planet_info['name']
        )
        
        danger_emoji = "🟢" if planet_info['danger_level'] <= 2 else "🟡" if planet_info['danger_level'] <= 3 else "🔴"
        
        embed = await create_bot_author_embed(
            title=f"{danger_emoji} {planet_info['name']} Market Analysis",
            description=f"*{planet_info['description']}*\n\n"
                       f"**Danger Level:** {planet_info['danger_level']}/5\n"
                       f"**Market Modifier:** {planet_info['market_modifier']:.1f}x\n"
                       f"**Jump Fuel Cost:** {planet_info['fuel_cost']} units",
            color=0x00ff88
        )
        
        for commodity in market_data:
            price = commodity['current_price']
            base_price = commodity['base_price']
            supply = commodity['supply_level']
            demand = commodity['demand_level']
            
            # Calculate profit potential
            profit_indicator = ""
            if price < base_price * 0.8:
                profit_indicator = "🟢 **EXCELLENT BUY**"
            elif price < base_price * 0.9:
                profit_indicator = "🟡 Good Buy"
            elif price > base_price * 1.2:
                profit_indicator = "🔴 **EXCELLENT SELL**"
            elif price > base_price * 1.1:
                profit_indicator = "🟡 Good Sell"
            else:
                profit_indicator = "⚪ Average"
            
            embed.add_field(
                name=f"💎 {commodity['commodity']}",
                value=f"**Price:** {price:,} credits\n"
                      f"**Supply:** {supply}/100 | **Demand:** {demand}/100\n"
                      f"**Status:** {profit_indicator}\n"
                      f"*{commodity['description']}*",
                inline=False
            )
        
        if planet_info['special_bonus']:
            embed.add_field(
                name="🌟 Special Bonus",
                value=planet_info['special_bonus'],
                inline=False
            )
        
        await send_message(embed=embed, inter=inter)

    @commands.slash_command(name="trade", description="Trading operations")
    async def trade_group(self, inter):
        pass

    @trade_group.sub_command(name="buy", description="Buy commodities at current planet")
    async def trade_buy(
        self,
        inter: disnake.AppCmdInter,
        commodity: str = commands.Param(description="Commodity to buy"),
        amount: int = commands.Param(description="Amount to buy")
    ):
        """Buy commodities at the current planet."""
        if amount <= 0:
            await send_message(
                msg="❌ Amount must be greater than 0!",
                inter=inter,
                ephemeral=True
            )
            return
        
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Get market price
        price_data = await db.execute_query(
            "SELECT current_price FROM market_prices WHERE planet = $1 AND LOWER(commodity) = LOWER($2)",
            player.current_planet, commodity
        )
        
        if not price_data:
            await send_message(
                msg="❌ Commodity not found! Available: Ore, Spice, Tech, Luxuries",
                inter=inter,
                ephemeral=True
            )
            return
        
        price_per_unit = price_data[0]['current_price']
        total_cost = price_per_unit * amount
        
        # Check if player has enough credits
        if player.credits < total_cost:
            await send_message(
                msg=f"❌ Insufficient credits! You need {total_cost:,} but only have {player.credits:,}.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Check cargo capacity
        ship = await player.get_ship()
        current_cargo = await player.get_total_cargo()
        
        if current_cargo + amount > ship['cargo_capacity']:
            available_space = ship['cargo_capacity'] - current_cargo
            await send_message(
                msg=f"❌ Insufficient cargo space! You can only carry {available_space} more units.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Execute trade
        commodity_name = commodity.title()
        
        # Update player credits
        player.credits -= total_cost
        player.total_trades += 1
        await player.save()
        
        # Update inventory
        current_inventory = await db.execute_query(
            "SELECT * FROM player_inventory WHERE user_id = $1 AND commodity = $2",
            player.user_id, commodity_name,
            user_id=player.user_id
        )
        
        if current_inventory:
            # Update existing inventory
            old_qty = current_inventory[0]['quantity']
            old_avg_price = current_inventory[0]['average_buy_price']
            new_qty = old_qty + amount
            new_avg_price = ((old_qty * old_avg_price) + (amount * price_per_unit)) / new_qty
            
            await db.execute_command(
                "UPDATE player_inventory SET quantity = $3, average_buy_price = $4 WHERE user_id = $1 AND commodity = $2",
                player.user_id, commodity_name, new_qty, new_avg_price,
                user_id=player.user_id
            )
        else:
            # Create new inventory entry
            await db.execute_command(
                "INSERT INTO player_inventory (user_id, commodity, quantity, average_buy_price) VALUES ($1, $2, $3, $4)",
                player.user_id, commodity_name, amount, price_per_unit,
                user_id=player.user_id
            )
        
        # Log trade
        await db.execute_command(
            """INSERT INTO trade_history (user_id, planet, commodity, action, quantity, price_per_unit, total_value)
               VALUES ($1, $2, $3, 'buy', $4, $5, $6)""",
            player.user_id, player.current_planet, commodity_name, amount, price_per_unit, total_cost,
            user_id=player.user_id
        )
        
        # Check achievements
        await player.check_achievements()
        
        embed = await create_bot_author_embed(
            title="✅ Trade Successful!",
            description=f"Purchased {amount:,} units of **{commodity_name}** for {total_cost:,} credits",
            color=0x00ff00
        )
        
        embed.add_field(name="Price per Unit", value=f"{price_per_unit:,} cr", inline=True)
        embed.add_field(name="Remaining Credits", value=f"{player.credits:,} cr", inline=True)
        embed.add_field(name="Cargo Space Used", value=f"{current_cargo + amount}/{ship['cargo_capacity']}", inline=True)
        
        await send_message(embed=embed, inter=inter)

    @trade_group.sub_command(name="sell", description="Sell commodities at current planet")
    async def trade_sell(
        self,
        inter: disnake.AppCmdInter,
        commodity: str = commands.Param(description="Commodity to sell"),
        amount: int = commands.Param(description="Amount to sell")
    ):
        """Sell commodities at the current planet."""
        if amount <= 0:
            await send_message(
                msg="❌ Amount must be greater than 0!",
                inter=inter,
                ephemeral=True
            )
            return
        
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        commodity_name = commodity.title()
        
        # Check inventory
        inventory = await db.execute_query(
            "SELECT * FROM player_inventory WHERE user_id = $1 AND commodity = $2",
            player.user_id, commodity_name,
            user_id=player.user_id
        )
        
        if not inventory or inventory[0]['quantity'] < amount:
            current_amount = inventory[0]['quantity'] if inventory else 0
            await send_message(
                msg=f"❌ Insufficient {commodity_name}! You have {current_amount} units.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Get current market price
        price_data = await db.execute_query(
            "SELECT current_price FROM market_prices WHERE planet = $1 AND commodity = $2",
            player.current_planet, commodity_name
        )
        
        if not price_data:
            await send_message(
                msg="❌ Cannot sell this commodity at current location!",
                inter=inter,
                ephemeral=True
            )
            return
        
        current_price = price_data[0]['current_price']
        total_revenue = current_price * amount
        
        # Calculate profit/loss
        avg_buy_price = inventory[0]['average_buy_price']
        profit_loss = (current_price - avg_buy_price) * amount
        
        # Execute sale
        player.credits += total_revenue
        player.total_trades += 1
        await player.save()
        
        # Update inventory
        new_quantity = inventory[0]['quantity'] - amount
        if new_quantity > 0:
            await db.execute_command(
                "UPDATE player_inventory SET quantity = $3 WHERE user_id = $1 AND commodity = $2",
                player.user_id, commodity_name, new_quantity,
                user_id=player.user_id
            )
        else:
            await db.execute_command(
                "DELETE FROM player_inventory WHERE user_id = $1 AND commodity = $2",
                player.user_id, commodity_name,
                user_id=player.user_id
            )
        
        # Log trade
        await db.execute_command(
            """INSERT INTO trade_history (user_id, planet, commodity, action, quantity, price_per_unit, total_value, profit_loss)
               VALUES ($1, $2, $3, 'sell', $4, $5, $6, $7)""",
            player.user_id, player.current_planet, commodity_name, amount, current_price, total_revenue, profit_loss,
            user_id=player.user_id
        )
        
        # Check achievements
        await player.check_achievements()
        
        # Create result embed
        profit_color = 0x00ff00 if profit_loss >= 0 else 0xff0000
        profit_text = f"+{profit_loss:,}" if profit_loss >= 0 else f"{profit_loss:,}"
        
        embed = await create_bot_author_embed(
            title="💰 Sale Completed!",
            description=f"Sold {amount:,} units of **{commodity_name}** for {total_revenue:,} credits",
            color=profit_color
        )
        
        embed.add_field(name="Price per Unit", value=f"{current_price:,} cr", inline=True)
        embed.add_field(name="Profit/Loss", value=f"{profit_text} cr", inline=True)
        embed.add_field(name="New Balance", value=f"{player.credits:,} cr", inline=True)
        
        await send_message(embed=embed, inter=inter)

    @trade_group.sub_command(name="inventory", description="View your cargo inventory")
    async def trade_inventory(self, inter: disnake.AppCmdInter):
        """Display player's current cargo inventory."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        inventory = await player.get_inventory()
        ship = await player.get_ship()
        
        embed = await create_bot_author_embed(
            title="📦 Cargo Manifest",
            description=f"**Ship:** {ship['name']}\n**Location:** {player.current_planet}",
            color=0x0099ff
        )
        
        total_cargo = 0
        total_value = 0
        
        if inventory:
            db = await get_db()
            
            for commodity, data in inventory.items():
                if data['quantity'] > 0:
                    total_cargo += data['quantity']
                    
                    # Get current market value
                    price_data = await db.execute_query(
                        "SELECT current_price FROM market_prices WHERE planet = $1 AND commodity = $2",
                        player.current_planet, commodity
                    )
                    
                    current_price = price_data[0]['current_price'] if price_data else 0
                    market_value = data['quantity'] * current_price
                    total_value += market_value
                    
                    # Calculate potential profit/loss
                    potential_profit = (current_price - data['average_buy_price']) * data['quantity']
                    profit_indicator = "📈" if potential_profit > 0 else "📉" if potential_profit < 0 else "➡️"
                    
                    embed.add_field(
                        name=f"{profit_indicator} {commodity}",
                        value=f"**Quantity:** {data['quantity']:,}\n"
                              f"**Avg. Buy Price:** {data['average_buy_price']:.0f} cr\n"
                              f"**Current Value:** {market_value:,} cr\n"
                              f"**Potential P/L:** {potential_profit:+,.0f} cr",
                        inline=True
                    )
        
        if total_cargo == 0:
            embed.add_field(
                name="Empty Hold",
                value="Your cargo bay is empty. Visit a market to start trading!",
                inline=False
            )
        
        embed.add_field(
            name="📊 Summary",
            value=f"**Cargo Used:** {total_cargo}/{ship['cargo_capacity']}\n"
                  f"**Current Value:** {total_value:,} cr\n"
                  f"**Available Space:** {ship['cargo_capacity'] - total_cargo}",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(Trading(bot))