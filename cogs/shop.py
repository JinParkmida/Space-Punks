import disnake
from disnake.ext import commands

from models.database import get_db
from models.player import Player
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Ship upgrades available for purchase
        self.upgrades = {
            'cargo_expansion': {
                'name': 'Cargo Bay Expansion',
                'description': 'Increase cargo capacity by 25 units',
                'cost': 5000,
                'effect': 'cargo_capacity',
                'value': 25,
                'max_level': 10
            },
            'fuel_efficiency': {
                'name': 'Engine Optimization',
                'description': 'Reduce fuel consumption by 10%',
                'cost': 8000,
                'effect': 'fuel_efficiency',
                'value': -0.1,
                'max_level': 5
            },
            'navigation_system': {
                'name': 'Advanced Navigation',
                'description': 'Increase jump success rate by 5%',
                'cost': 12000,
                'effect': 'jump_success_bonus',
                'value': 0.05,
                'max_level': 4
            },
            'shield_upgrade': {
                'name': 'Shield Generator',
                'description': 'Improve defensive capabilities',
                'cost': 6000,
                'effect': 'shield_strength',
                'value': 1,
                'max_level': 5
            },
            'engine_boost': {
                'name': 'Engine Boost Module',
                'description': 'Increase engine speed rating',
                'cost': 4000,
                'effect': 'engine_speed',
                'value': 1,
                'max_level': 5
            }
        }
        
        # Paint jobs for ship customization
        self.paint_jobs = {
            'crimson_flame': {
                'name': 'Crimson Flame',
                'description': 'Blazing red paint with flame patterns',
                'cost': 2000
            },
            'void_black': {
                'name': 'Void Black',
                'description': 'Stealth black coating for discrete operations',
                'cost': 2500
            },
            'stellar_blue': {
                'name': 'Stellar Blue',
                'description': 'Deep blue with star field patterns',
                'cost': 1800
            },
            'golden_luxury': {
                'name': 'Golden Luxury',
                'description': 'Premium gold finish for successful traders',
                'cost': 5000
            },
            'neon_green': {
                'name': 'Neon Green',
                'description': 'Bright green with energy patterns',
                'cost': 2200
            }
        }

    @commands.slash_command(name="shop", description="Browse available ship upgrades and customizations")
    async def shop(self, inter: disnake.AppCmdInter):
        """Display the ship upgrade shop."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        ship = await player.get_ship()
        
        embed = await create_bot_author_embed(
            title="🛒 Galactic Ship Emporium",
            description=f"**Your Credits:** {player.credits:,}\n"
                       f"**Current Ship:** {ship['name']}",
            color=0x00ccff
        )
        
        # Performance Upgrades
        upgrade_text = ""
        for upgrade_id, upgrade in self.upgrades.items():
            # Calculate current level based on ship stats
            current_level = self._get_current_upgrade_level(ship, upgrade)
            max_level = upgrade['max_level']
            
            if current_level >= max_level:
                status = "✅ MAXED"
                cost_text = "---"
            else:
                status = f"Level {current_level}/{max_level}"
                # Scale cost based on current level
                scaled_cost = upgrade['cost'] * (1 + current_level * 0.5)
                cost_text = f"{scaled_cost:,.0f} cr"
            
            affordable = "💰" if player.credits >= upgrade['cost'] * (1 + current_level * 0.5) else "❌"
            
            upgrade_text += f"{affordable} **{upgrade['name']}** - {cost_text}\n"
            upgrade_text += f"   {upgrade['description']} ({status})\n\n"
        
        embed.add_field(
            name="⚙️ Performance Upgrades",
            value=upgrade_text,
            inline=False
        )
        
        # Paint Jobs
        paint_text = ""
        for paint_id, paint in self.paint_jobs.items():
            if ship['paint_job'] == paint['name']:
                status = "✅ EQUIPPED"
                cost_text = "---"
                affordable = "✅"
            else:
                status = "Available"
                cost_text = f"{paint['cost']:,} cr"
                affordable = "💰" if player.credits >= paint['cost'] else "❌"
            
            paint_text += f"{affordable} **{paint['name']}** - {cost_text}\n"
            paint_text += f"   {paint['description']} ({status})\n\n"
        
        embed.add_field(
            name="🎨 Paint Jobs",
            value=paint_text,
            inline=False
        )
        
        # Fuel
        fuel_cost_per_unit = 10
        max_fuel_purchase = min(100, (player.credits // fuel_cost_per_unit))
        
        embed.add_field(
            name="⛽ Fuel Station",
            value=f"**Fuel Price:** {fuel_cost_per_unit} cr per unit\n"
                  f"**Current Fuel:** {player.fuel} units\n"
                  f"**Max Purchase:** {max_fuel_purchase} units\n"
                  f"Use `/buy fuel <amount>` to refuel",
            inline=False
        )
        
        embed.set_footer(text="Use /buy upgrade <name> or /buy paint <name> to purchase!")
        
        await send_message(embed=embed, inter=inter)

    def _get_current_upgrade_level(self, ship, upgrade):
        """Calculate current upgrade level based on ship stats."""
        effect = upgrade['effect']
        base_values = {
            'cargo_capacity': 50,
            'fuel_efficiency': 1.0,
            'jump_success_bonus': 0.0,
            'shield_strength': 0,
            'engine_speed': 1
        }
        
        current_value = ship[effect]
        base_value = base_values[effect]
        upgrade_value = upgrade['value']
        
        if effect == 'fuel_efficiency':
            # Fuel efficiency decreases (improvement), so calculate differently
            return int((base_value - current_value) / abs(upgrade_value))
        else:
            # Other stats increase
            return int((current_value - base_value) / upgrade_value)

    @commands.slash_command(name="buy", description="Purchase upgrades, paint jobs, or fuel")
    async def buy_group(self, inter):
        pass

    @buy_group.sub_command(name="upgrade", description="Buy a ship upgrade")
    async def buy_upgrade(
        self,
        inter: disnake.AppCmdInter,
        upgrade_name: str = commands.Param(description="Name of upgrade to purchase")
    ):
        """Purchase a ship upgrade."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        ship = await player.get_ship()
        db = await get_db()
        
        # Find upgrade
        upgrade_id = None
        for uid, upgrade in self.upgrades.items():
            if upgrade_name.lower() in upgrade['name'].lower():
                upgrade_id = uid
                break
        
        if not upgrade_id:
            await send_message(
                msg="❌ Upgrade not found! Use `/shop` to see available upgrades.",
                inter=inter,
                ephemeral=True
            )
            return
        
        upgrade = self.upgrades[upgrade_id]
        current_level = self._get_current_upgrade_level(ship, upgrade)
        
        # Check if already maxed
        if current_level >= upgrade['max_level']:
            await send_message(
                msg=f"❌ **{upgrade['name']}** is already at maximum level!",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Calculate cost (scales with level)
        scaled_cost = int(upgrade['cost'] * (1 + current_level * 0.5))
        
        # Check if player can afford it
        if player.credits < scaled_cost:
            await send_message(
                msg=f"❌ Insufficient credits! You need {scaled_cost:,} but only have {player.credits:,}.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Apply upgrade
        player.credits -= scaled_cost
        await player.save()
        
        # Update ship stats
        effect = upgrade['effect']
        new_value = ship[effect] + upgrade['value']
        
        await db.execute_command(
            f"UPDATE ships SET {effect} = $2, total_upgrade_cost = total_upgrade_cost + $3 WHERE user_id = $1",
            player.user_id, new_value, scaled_cost,
            user_id=player.user_id
        )
        
        embed = await create_bot_author_embed(
            title="✅ Upgrade Installed!",
            description=f"Successfully installed **{upgrade['name']}**!",
            color=0x00ff00
        )
        
        embed.add_field(name="Cost", value=f"{scaled_cost:,} credits", inline=True)
        embed.add_field(name="New Level", value=f"{current_level + 1}/{upgrade['max_level']}", inline=True)
        embed.add_field(name="Remaining Credits", value=f"{player.credits:,} cr", inline=True)
        embed.add_field(name="Effect", value=upgrade['description'], inline=False)
        
        await send_message(embed=embed, inter=inter)

    @buy_group.sub_command(name="paint", description="Buy a paint job for your ship")
    async def buy_paint(
        self,
        inter: disnake.AppCmdInter,
        paint_name: str = commands.Param(description="Name of paint job to purchase")
    ):
        """Purchase a paint job for ship customization."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        ship = await player.get_ship()
        db = await get_db()
        
        # Find paint job
        paint_id = None
        for pid, paint in self.paint_jobs.items():
            if paint_name.lower() in paint['name'].lower():
                paint_id = pid
                break
        
        if not paint_id:
            await send_message(
                msg="❌ Paint job not found! Use `/shop` to see available options.",
                inter=inter,
                ephemeral=True
            )
            return
        
        paint = self.paint_jobs[paint_id]
        
        # Check if already equipped
        if ship['paint_job'] == paint['name']:
            await send_message(
                msg=f"❌ **{paint['name']}** is already equipped on your ship!",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Check if player can afford it
        if player.credits < paint['cost']:
            await send_message(
                msg=f"❌ Insufficient credits! You need {paint['cost']:,} but only have {player.credits:,}.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Apply paint job
        player.credits -= paint['cost']
        await player.save()
        
        await db.execute_command(
            "UPDATE ships SET paint_job = $2, total_upgrade_cost = total_upgrade_cost + $3 WHERE user_id = $1",
            player.user_id, paint['name'], paint['cost'],
            user_id=player.user_id
        )
        
        embed = await create_bot_author_embed(
            title="🎨 Paint Job Applied!",
            description=f"Your ship now sports the **{paint['name']}** paint job!",
            color=0x00ff00
        )
        
        embed.add_field(name="Cost", value=f"{paint['cost']:,} credits", inline=True)
        embed.add_field(name="Remaining Credits", value=f"{player.credits:,} cr", inline=True)
        embed.add_field(name="Description", value=paint['description'], inline=False)
        
        await send_message(embed=embed, inter=inter)

    @buy_group.sub_command(name="fuel", description="Purchase fuel for your ship")
    async def buy_fuel(
        self,
        inter: disnake.AppCmdInter,
        amount: int = commands.Param(description="Amount of fuel to purchase")
    ):
        """Purchase fuel for interstellar travel."""
        if amount <= 0:
            await send_message(
                msg="❌ Amount must be greater than 0!",
                inter=inter,
                ephemeral=True
            )
            return
        
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        
        fuel_cost_per_unit = 10
        total_cost = amount * fuel_cost_per_unit
        
        # Check if player can afford it
        if player.credits < total_cost:
            max_affordable = player.credits // fuel_cost_per_unit
            await send_message(
                msg=f"❌ Insufficient credits! You can afford {max_affordable} units for {max_affordable * fuel_cost_per_unit:,} credits.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Check fuel capacity (max 1000 units)
        max_fuel = 1000
        if player.fuel + amount > max_fuel:
            available_capacity = max_fuel - player.fuel
            await send_message(
                msg=f"❌ Fuel tank capacity exceeded! You can only add {available_capacity} more units.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Purchase fuel
        player.credits -= total_cost
        player.fuel += amount
        await player.save()
        
        embed = await create_bot_author_embed(
            title="⛽ Fuel Purchased!",
            description=f"Added {amount} units of fuel to your ship.",
            color=0x00ff00
        )
        
        embed.add_field(name="Cost", value=f"{total_cost:,} credits", inline=True)
        embed.add_field(name="New Fuel Level", value=f"{player.fuel}/1000 units", inline=True)
        embed.add_field(name="Remaining Credits", value=f"{player.credits:,} cr", inline=True)
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(Shop(bot))