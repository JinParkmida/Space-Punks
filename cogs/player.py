import disnake
from disnake.ext import commands
from typing import Optional

from models.database import get_db
from models.player import Player
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class PlayerManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="profile", description="View player profile and statistics")
    async def profile(
        self,
        inter: disnake.AppCmdInter,
        pilot: Optional[disnake.Member] = commands.Param(default=None, description="Pilot to view (default: yourself)")
    ):
        """Display comprehensive player profile and statistics."""
        target_user = pilot if pilot else inter.author
        player = await Player.get_or_create(target_user.id, target_user.display_name)
        db = await get_db()
        
        # Calculate net worth
        net_worth = await player.calculate_net_worth()
        
        # Get ship info
        ship = await player.get_ship()
        
        # Get faction info
        faction_name = "Independent"
        if player.faction_id:
            faction_data = await db.execute_query(
                "SELECT name FROM factions WHERE id = $1",
                player.faction_id
            )
            if faction_data:
                faction_name = faction_data[0]['name']
        
        # Get achievements
        achievements = await db.execute_query(
            """SELECT a.name, a.badge_emoji 
               FROM player_achievements pa
               JOIN achievements a ON pa.achievement_id = a.id
               WHERE pa.user_id = $1
               ORDER BY pa.unlocked_at DESC""",
            player.user_id,
            user_id=player.user_id
        )
        
        # Calculate success rates
        jump_success_rate = (player.successful_jumps / max(player.total_jumps, 1)) * 100
        
        embed = await create_bot_author_embed(
            title=f"👨‍🚀 Pilot Profile: {target_user.display_name}",
            description=f"**Current Location:** {player.current_planet}\n"
                       f"**Faction:** {faction_name}",
            color=0x00aaff
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Financial Status
        embed.add_field(
            name="💰 Financial Status",
            value=f"**Credits:** {player.credits:,}\n"
                  f"**Net Worth:** {net_worth:,}\n"
                  f"**Fuel:** {player.fuel} units",
            inline=True
        )
        
        # Trading Statistics
        embed.add_field(
            name="📈 Trading Stats",
            value=f"**Total Trades:** {player.total_trades:,}\n"
                  f"**Jump Success:** {player.successful_jumps}/{player.total_jumps}\n"
                  f"**Success Rate:** {jump_success_rate:.1f}%",
            inline=True
        )
        
        # Ship Information
        embed.add_field(
            name="🛸 Ship: " + ship['name'],
            value=f"**Cargo:** {ship['cargo_capacity']} units\n"
                  f"**Fuel Efficiency:** {ship['fuel_efficiency']:.1f}x\n"
                  f"**Jump Bonus:** +{ship['jump_success_bonus']:.1%}",
            inline=True
        )
        
        # Recent achievements (last 3)
        if achievements:
            recent_achievements = achievements[:3]
            achievement_text = ""
            for achievement in recent_achievements:
                achievement_text += f"{achievement['badge_emoji']} {achievement['name']}\n"
            
            embed.add_field(
                name="🏆 Recent Achievements",
                value=achievement_text,
                inline=False
            )
        
        # Get recent trade history
        recent_trades = await db.execute_query(
            """SELECT planet, commodity, action, quantity, total_value, timestamp
               FROM trade_history 
               WHERE user_id = $1 
               ORDER BY timestamp DESC 
               LIMIT 3""",
            player.user_id,
            user_id=player.user_id
        )
        
        if recent_trades:
            trade_text = ""
            for trade in recent_trades:
                action_emoji = "📈" if trade['action'] == 'buy' else "📉"
                trade_text += f"{action_emoji} {trade['action'].title()} {trade['quantity']} {trade['commodity']} at {trade['planet']}\n"
            
            embed.add_field(
                name="📊 Recent Trades",
                value=trade_text,
                inline=False
            )
        
        await send_message(embed=embed, inter=inter)

    @commands.slash_command(name="ship", description="View ship status and upgrade information")
    async def ship(self, inter: disnake.AppCmdInter):
        """Display detailed ship information and upgrade status."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        ship = await player.get_ship()
        
        # Calculate current cargo
        current_cargo = await player.get_total_cargo()
        cargo_percentage = (current_cargo / ship['cargo_capacity']) * 100
        
        embed = await create_bot_author_embed(
            title=f"🛸 Ship Status: {ship['name']}",
            description=f"**Owner:** {inter.author.display_name}\n"
                       f"**Location:** {player.current_planet}",
            color=0x0066cc
        )
        
        # Cargo Status
        cargo_bar = "█" * int(cargo_percentage / 10) + "░" * (10 - int(cargo_percentage / 10))
        embed.add_field(
            name="📦 Cargo Bay",
            value=f"**Capacity:** {current_cargo}/{ship['cargo_capacity']} units\n"
                  f"**Usage:** {cargo_percentage:.1f}%\n"
                  f"`{cargo_bar}`",
            inline=False
        )
        
        # Ship Systems
        embed.add_field(
            name="⚙️ Engine Systems",
            value=f"**Fuel Efficiency:** {ship['fuel_efficiency']:.1f}x\n"
                  f"**Engine Speed:** Level {ship['engine_speed']}\n"
                  f"**Current Fuel:** {player.fuel} units",
            inline=True
        )
        
        embed.add_field(
            name="🛡️ Defense Systems",
            value=f"**Shield Strength:** Level {ship['shield_strength']}\n"
                  f"**Jump Success Bonus:** +{ship['jump_success_bonus']:.1%}\n"
                  f"**Navigation System:** Level {ship['navigation_system']}",
            inline=True
        )
        
        embed.add_field(
            name="🎨 Customization",
            value=f"**Paint Job:** {ship['paint_job']}\n"
                  f"**Total Upgrades Cost:** {ship['total_upgrade_cost']:,} cr",
            inline=True
        )
        
        # Upgrade recommendations
        recommendations = []
        if ship['cargo_capacity'] < 100:
            recommendations.append("📦 Expand cargo bay for more trading capacity")
        if ship['fuel_efficiency'] > 0.8:
            recommendations.append("⛽ Upgrade engines for better fuel efficiency")
        if ship['jump_success_bonus'] < 0.1:
            recommendations.append("🎯 Improve navigation for safer jumps")
        
        if recommendations:
            embed.add_field(
                name="💡 Upgrade Recommendations",
                value="\n".join(recommendations),
                inline=False
            )
        
        embed.set_footer(text="Use /shop to browse available upgrades!")
        
        await send_message(embed=embed, inter=inter)

    @commands.slash_command(name="achievements", description="View your achievements and progress")
    async def achievements(self, inter: disnake.AppCmdInter):
        """Display player achievements and progress tracking."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Get all achievements with unlock status
        all_achievements = await db.execute_query(
            """SELECT a.*, 
                      CASE WHEN pa.user_id IS NOT NULL THEN true ELSE false END as unlocked,
                      pa.unlocked_at
               FROM achievements a
               LEFT JOIN player_achievements pa ON a.id = pa.achievement_id AND pa.user_id = $1
               ORDER BY unlocked DESC, a.requirement_value ASC""",
            player.user_id,
            user_id=player.user_id
        )
        
        unlocked_count = sum(1 for a in all_achievements if a['unlocked'])
        total_count = len(all_achievements)
        
        embed = await create_bot_author_embed(
            title="🏆 Achievement Progress",
            description=f"**Progress:** {unlocked_count}/{total_count} achievements unlocked\n"
                       f"**Completion:** {(unlocked_count/total_count)*100:.1f}%",
            color=0xffd700
        )
        
        # Unlocked achievements
        unlocked_achievements = [a for a in all_achievements if a['unlocked']]
        if unlocked_achievements:
            unlocked_text = ""
            for achievement in unlocked_achievements[:8]:  # Show first 8
                unlocked_text += f"{achievement['badge_emoji']} **{achievement['name']}**\n"
                unlocked_text += f"*{achievement['description']}*\n\n"
            
            if len(unlocked_achievements) > 8:
                unlocked_text += f"... and {len(unlocked_achievements) - 8} more!"
            
            embed.add_field(
                name="✅ Unlocked Achievements",
                value=unlocked_text,
                inline=False
            )
        
        # Progress on locked achievements
        locked_achievements = [a for a in all_achievements if not a['unlocked']]
        if locked_achievements:
            progress_text = ""
            for achievement in locked_achievements[:5]:  # Show first 5
                # Calculate progress based on requirement type
                current_value = 0
                if achievement['requirement_type'] == 'trades':
                    current_value = player.total_trades
                elif achievement['requirement_type'] == 'jumps':
                    current_value = player.total_jumps
                elif achievement['requirement_type'] == 'credits':
                    current_value = player.credits
                elif achievement['requirement_type'] == 'net_worth':
                    current_value = await player.calculate_net_worth()
                elif achievement['requirement_type'] == 'faction_joined':
                    current_value = 1 if player.faction_id else 0
                
                progress_percentage = min((current_value / achievement['requirement_value']) * 100, 100)
                progress_bar = "█" * int(progress_percentage / 10) + "░" * (10 - int(progress_percentage / 10))
                
                progress_text += f"🔒 **{achievement['name']}** ({progress_percentage:.0f}%)\n"
                progress_text += f"`{progress_bar}`\n"
                progress_text += f"*{achievement['description']}*\n\n"
            
            embed.add_field(
                name="🎯 In Progress",
                value=progress_text,
                inline=False
            )
        
        # Total rewards earned
        total_rewards = await db.execute_query(
            """SELECT COALESCE(SUM(a.reward_credits), 0) as total_rewards
               FROM player_achievements pa
               JOIN achievements a ON pa.achievement_id = a.id
               WHERE pa.user_id = $1""",
            player.user_id,
            user_id=player.user_id
        )
        
        if total_rewards:
            embed.set_footer(text=f"Total achievement rewards earned: {total_rewards[0]['total_rewards']:,} credits")
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(PlayerManagement(bot))