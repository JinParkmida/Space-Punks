import disnake
from disnake.ext import commands
import random
from typing import Dict, Any

from models.database import get_db
from models.player import Player
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class Travel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Encounter types and their outcomes
        self.encounters = {
            'pirate_ambush': {
                'name': 'Pirate Ambush',
                'emoji': '🏴‍☠️',
                'description': 'Space pirates demand tribute!',
                'success_rate': 0.6,
                'success_reward': (500, 1500),
                'failure_penalty': (200, 800)
            },
            'cosmic_storm': {
                'name': 'Cosmic Storm',
                'emoji': '⛈️',
                'description': 'Dangerous energy storms block your path!',
                'success_rate': 0.7,
                'success_reward': (200, 600),
                'failure_penalty': (100, 400)
            },
            'hidden_cache': {
                'name': 'Hidden Cache',
                'emoji': '💎',
                'description': 'You discover an abandoned cargo cache!',
                'success_rate': 0.8,
                'success_reward': (800, 2000),
                'failure_penalty': (0, 0)
            },
            'merchant_convoy': {
                'name': 'Merchant Convoy',
                'emoji': '🚛',
                'description': 'Friendly traders offer a deal!',
                'success_rate': 0.9,
                'success_reward': (300, 800),
                'failure_penalty': (0, 100)
            },
            'derelict_salvage': {
                'name': 'Derelict Ship',
                'emoji': '🛸',
                'description': 'An abandoned ship drifts in space...',
                'success_rate': 0.65,
                'success_reward': (600, 1200),
                'failure_penalty': (150, 500)
            },
            'peaceful_dock': {
                'name': 'Safe Passage',
                'emoji': '✅',
                'description': 'Uneventful journey through safe space.',
                'success_rate': 1.0,
                'success_reward': (50, 200),
                'failure_penalty': (0, 0)
            }
        }

    @commands.slash_command(name="jump", description="Travel to another planet")
    async def jump(
        self,
        inter: disnake.AppCmdInter,
        planet: str = commands.Param(description="Destination planet")
    ):
        """Jump to another planet with random encounters."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Validate destination
        planet_data = await db.execute_query(
            "SELECT * FROM planets WHERE LOWER(name) = LOWER($1)",
            planet
        )
        
        if not planet_data:
            await send_message(
                msg="❌ Planet not found! Use `/location` to see available destinations.",
                inter=inter,
                ephemeral=True
            )
            return
        
        destination = planet_data[0]
        
        if destination['name'] == player.current_planet:
            await send_message(
                msg="❌ You're already at this planet!",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Check fuel requirements
        ship = await player.get_ship()
        fuel_cost = int(destination['fuel_cost'] * ship['fuel_efficiency'])
        
        if player.fuel < fuel_cost:
            await send_message(
                msg=f"❌ Insufficient fuel! Need {fuel_cost} units, have {player.fuel}.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Consume fuel
        player.fuel -= fuel_cost
        player.total_jumps += 1
        
        # Calculate encounter probability based on danger level
        danger_level = destination['danger_level']
        encounter_chance = min(0.2 + (danger_level * 0.15), 0.9)
        
        # Determine encounter type
        if random.random() < encounter_chance:
            # Weight encounters by danger level
            if danger_level <= 2:
                encounter_weights = [0.1, 0.2, 0.2, 0.3, 0.1, 0.1]  # Safer encounters
            elif danger_level <= 3:
                encounter_weights = [0.2, 0.2, 0.2, 0.2, 0.15, 0.05]  # Balanced
            else:
                encounter_weights = [0.3, 0.25, 0.15, 0.1, 0.15, 0.05]  # Dangerous encounters
            
            encounter_type = random.choices(
                list(self.encounters.keys()),
                weights=encounter_weights
            )[0]
        else:
            encounter_type = 'peaceful_dock'
        
        encounter = self.encounters[encounter_type]
        
        # Calculate success chance with ship bonuses
        base_success_rate = encounter['success_rate']
        ship_bonus = ship['jump_success_bonus']
        
        # Faction bonus
        faction_bonus = 0.0
        if player.faction_id:
            faction_data = await db.execute_query(
                "SELECT jump_bonus FROM factions WHERE id = $1",
                player.faction_id
            )
            if faction_data:
                faction_bonus = faction_data[0]['jump_bonus']
        
        final_success_rate = min(base_success_rate + ship_bonus + faction_bonus, 0.95)
        success = random.random() < final_success_rate
        
        # Calculate rewards/penalties
        if success:
            reward_range = encounter['success_reward']
            credits_gained = random.randint(reward_range[0], reward_range[1])
            player.credits += credits_gained
            player.successful_jumps += 1
            result_text = f"Success! Gained {credits_gained:,} credits."
            result_color = 0x00ff00
        else:
            penalty_range = encounter['failure_penalty']
            credits_lost = random.randint(penalty_range[0], penalty_range[1])
            player.credits = max(0, player.credits - credits_lost)
            result_text = f"Failed! Lost {credits_lost:,} credits."
            result_color = 0xff0000
            credits_gained = -credits_lost
        
        # Update player location
        old_planet = player.current_planet
        player.current_planet = destination['name']
        await player.save()
        
        # Log jump
        await db.execute_command(
            """INSERT INTO jump_history (user_id, from_planet, to_planet, encounter_type, 
                                       encounter_result, credits_gained, fuel_cost, success)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
            player.user_id, old_planet, destination['name'], encounter_type,
            result_text, credits_gained, fuel_cost, success,
            user_id=player.user_id
        )
        
        # Check achievements
        await player.check_achievements()
        
        # Create result embed
        embed = await create_bot_author_embed(
            title=f"🚀 Jump to {destination['name']}",
            description=f"**Encounter:** {encounter['emoji']} {encounter['name']}\n"
                       f"{encounter['description']}\n\n"
                       f"**Result:** {result_text}",
            color=result_color
        )
        
        embed.add_field(name="Fuel Used", value=f"{fuel_cost} units", inline=True)
        embed.add_field(name="Remaining Fuel", value=f"{player.fuel} units", inline=True)
        embed.add_field(name="Success Rate", value=f"{final_success_rate:.1%}", inline=True)
        embed.add_field(name="Credits", value=f"{player.credits:,} cr", inline=True)
        embed.add_field(name="Jump Success Rate", value=f"{player.successful_jumps}/{player.total_jumps} ({player.successful_jumps/max(player.total_jumps,1):.1%})", inline=True)
        
        # Add special planet info
        if destination['special_bonus']:
            embed.add_field(
                name="🌟 Planet Bonus",
                value=destination['special_bonus'],
                inline=False
            )
        
        await send_message(embed=embed, inter=inter)

    @commands.slash_command(name="location", description="View current location and travel options")
    async def location(self, inter: disnake.AppCmdInter):
        """Display current location and available destinations."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Get current planet info
        current_planet_data = await db.execute_query(
            "SELECT * FROM planets WHERE name = $1",
            player.current_planet
        )
        
        if not current_planet_data:
            await send_message(
                msg="❌ Error: Current location not found!",
                inter=inter,
                ephemeral=True
            )
            return
        
        current_planet = current_planet_data[0]
        
        # Get all other planets
        other_planets = await db.execute_query(
            "SELECT * FROM planets WHERE name != $1 ORDER BY danger_level, name",
            player.current_planet
        )
        
        ship = await player.get_ship()
        
        embed = await create_bot_author_embed(
            title=f"📍 Current Location: {player.current_planet}",
            description=f"*{current_planet['description']}*\n\n"
                       f"**Danger Level:** {current_planet['danger_level']}/5\n"
                       f"**Current Fuel:** {player.fuel} units",
            color=0x0099ff
        )
        
        # Add destinations
        destinations_text = ""
        for planet in other_planets:
            fuel_cost = int(planet['fuel_cost'] * ship['fuel_efficiency'])
            danger_emoji = "🟢" if planet['danger_level'] <= 2 else "🟡" if planet['danger_level'] <= 3 else "🔴"
            
            # Check if player can afford the jump
            if player.fuel >= fuel_cost:
                status = "✅"
            else:
                status = "❌"
            
            destinations_text += f"{status} {danger_emoji} **{planet['name']}** - {fuel_cost} fuel (Danger: {planet['danger_level']}/5)\n"
        
        embed.add_field(
            name="🚀 Available Destinations",
            value=destinations_text,
            inline=False
        )
        
        embed.add_field(
            name="🛸 Ship Status",
            value=f"**Name:** {ship['name']}\n"
                  f"**Fuel Efficiency:** {ship['fuel_efficiency']:.1f}x\n"
                  f"**Jump Success Bonus:** +{ship['jump_success_bonus']:.1%}",
            inline=True
        )
        
        # Add faction bonus if applicable
        if player.faction_id:
            faction_data = await db.execute_query(
                "SELECT name, jump_bonus FROM factions WHERE id = $1",
                player.faction_id
            )
            if faction_data:
                faction = faction_data[0]
                embed.add_field(
                    name="🏛️ Faction Bonus",
                    value=f"**{faction['name']}**\n"
                          f"Jump Success: +{faction['jump_bonus']:.1%}",
                    inline=True
                )
        
        embed.set_footer(text="💡 Use /jump <planet> to travel. Higher danger = better rewards!")
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(Travel(bot))