import disnake
from disnake.ext import commands

from models.database import get_db
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class Leaderboards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="leaderboard", description="View galactic leaderboards")
    async def leaderboard(
        self,
        inter: disnake.AppCmdInter,
        category: str = commands.Param(
            description="Leaderboard category",
            choices=["net_worth", "trades", "jumps", "success_rate", "faction_contribution"]
        )
    ):
        """Display various leaderboards for player rankings."""
        db = await get_db()
        
        if category == "net_worth":
            await self._show_net_worth_leaderboard(inter, db)
        elif category == "trades":
            await self._show_trades_leaderboard(inter, db)
        elif category == "jumps":
            await self._show_jumps_leaderboard(inter, db)
        elif category == "success_rate":
            await self._show_success_rate_leaderboard(inter, db)
        elif category == "faction_contribution":
            await self._show_faction_contribution_leaderboard(inter, db)

    async def _show_net_worth_leaderboard(self, inter, db):
        """Show net worth leaderboard."""
        players = await db.execute_query(
            """SELECT username, net_worth, current_planet, 
                      CASE WHEN faction_id IS NOT NULL THEN f.name ELSE 'Independent' END as faction_name
               FROM players p
               LEFT JOIN factions f ON p.faction_id = f.id
               ORDER BY net_worth DESC
               LIMIT 15"""
        )
        
        embed = await create_bot_author_embed(
            title="💎 Galactic Wealth Rankings",
            description="The richest pilots in the galaxy",
            color=0xffd700
        )
        
        leaderboard_text = ""
        for i, player in enumerate(players, 1):
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{player['username']}** - {player['net_worth']:,} cr\n"
            leaderboard_text += f"   📍 {player['current_planet']} | 🏛️ {player['faction_name']}\n\n"
        
        embed.add_field(
            name="🏆 Top Traders",
            value=leaderboard_text or "No data available",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)

    async def _show_trades_leaderboard(self, inter, db):
        """Show total trades leaderboard."""
        players = await db.execute_query(
            """SELECT username, total_trades, net_worth,
                      CASE WHEN faction_id IS NOT NULL THEN f.name ELSE 'Independent' END as faction_name
               FROM players p
               LEFT JOIN factions f ON p.faction_id = f.id
               WHERE total_trades > 0
               ORDER BY total_trades DESC
               LIMIT 15"""
        )
        
        embed = await create_bot_author_embed(
            title="📈 Most Active Traders",
            description="Pilots with the most completed trades",
            color=0x00ff88
        )
        
        leaderboard_text = ""
        for i, player in enumerate(players, 1):
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{player['username']}** - {player['total_trades']:,} trades\n"
            leaderboard_text += f"   💰 {player['net_worth']:,} cr | 🏛️ {player['faction_name']}\n\n"
        
        embed.add_field(
            name="🏆 Trading Champions",
            value=leaderboard_text or "No data available",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)

    async def _show_jumps_leaderboard(self, inter, db):
        """Show total jumps leaderboard."""
        players = await db.execute_query(
            """SELECT username, total_jumps, successful_jumps, net_worth,
                      CASE WHEN faction_id IS NOT NULL THEN f.name ELSE 'Independent' END as faction_name
               FROM players p
               LEFT JOIN factions f ON p.faction_id = f.id
               WHERE total_jumps > 0
               ORDER BY total_jumps DESC
               LIMIT 15"""
        )
        
        embed = await create_bot_author_embed(
            title="🚀 Galactic Explorers",
            description="Pilots with the most interstellar jumps",
            color=0x0099ff
        )
        
        leaderboard_text = ""
        for i, player in enumerate(players, 1):
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            success_rate = (player['successful_jumps'] / player['total_jumps']) * 100
            leaderboard_text += f"{medal} **{player['username']}** - {player['total_jumps']:,} jumps\n"
            leaderboard_text += f"   ✅ {success_rate:.1f}% success | 🏛️ {player['faction_name']}\n\n"
        
        embed.add_field(
            name="🏆 Space Pioneers",
            value=leaderboard_text or "No data available",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)

    async def _show_success_rate_leaderboard(self, inter, db):
        """Show jump success rate leaderboard."""
        players = await db.execute_query(
            """SELECT username, total_jumps, successful_jumps, net_worth,
                      CASE WHEN faction_id IS NOT NULL THEN f.name ELSE 'Independent' END as faction_name,
                      (successful_jumps::float / GREATEST(total_jumps, 1)) * 100 as success_rate
               FROM players p
               LEFT JOIN factions f ON p.faction_id = f.id
               WHERE total_jumps >= 10
               ORDER BY success_rate DESC, total_jumps DESC
               LIMIT 15"""
        )
        
        embed = await create_bot_author_embed(
            title="🎯 Master Navigators",
            description="Pilots with the highest jump success rates (minimum 10 jumps)",
            color=0xff6600
        )
        
        leaderboard_text = ""
        for i, player in enumerate(players, 1):
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{player['username']}** - {player['success_rate']:.1f}%\n"
            leaderboard_text += f"   🚀 {player['successful_jumps']}/{player['total_jumps']} | 🏛️ {player['faction_name']}\n\n"
        
        embed.add_field(
            name="🏆 Elite Pilots",
            value=leaderboard_text or "No data available",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)

    async def _show_faction_contribution_leaderboard(self, inter, db):
        """Show faction contribution leaderboard."""
        # Get faction standings
        factions = await db.execute_query(
            """SELECT f.name, f.member_count, f.total_contribution,
                      COALESCE(AVG(p.net_worth), 0) as avg_member_wealth
               FROM factions f
               LEFT JOIN players p ON f.id = p.faction_id
               GROUP BY f.id, f.name, f.member_count, f.total_contribution
               ORDER BY f.total_contribution DESC"""
        )
        
        embed = await create_bot_author_embed(
            title="🏛️ Faction Power Rankings",
            description="Faction standings by total contribution and influence",
            color=0x9966cc
        )
        
        faction_text = ""
        for i, faction in enumerate(factions, 1):
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            faction_text += f"{medal} **{faction['name']}**\n"
            faction_text += f"   💰 {faction['total_contribution']:,} cr total\n"
            faction_text += f"   👥 {faction['member_count']} members\n"
            faction_text += f"   📊 {faction['avg_member_wealth']:,.0f} cr avg wealth\n\n"
        
        embed.add_field(
            name="🏆 Faction Rankings",
            value=faction_text or "No factions found",
            inline=False
        )
        
        # Get top individual contributors
        top_contributors = await db.execute_query(
            """SELECT p.username, f.name as faction_name,
                      COALESCE(SUM(th.total_value), 0) as total_contribution
               FROM players p
               JOIN factions f ON p.faction_id = f.id
               LEFT JOIN trade_history th ON p.user_id = th.user_id
               GROUP BY p.user_id, p.username, f.name
               ORDER BY total_contribution DESC
               LIMIT 10"""
        )
        
        if top_contributors:
            contributor_text = ""
            for i, contributor in enumerate(top_contributors, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                contributor_text += f"{medal} **{contributor['username']}** ({contributor['faction_name']})\n"
                contributor_text += f"   💎 {contributor['total_contribution']:,} cr contributed\n\n"
            
            embed.add_field(
                name="🌟 Top Individual Contributors",
                value=contributor_text,
                inline=False
            )
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(Leaderboards(bot))