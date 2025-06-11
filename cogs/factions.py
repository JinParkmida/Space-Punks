import disnake
from disnake.ext import commands
from typing import Optional

from models.database import get_db
from models.player import Player
from cogs.helper import send_message
from util.botembed import create_bot_author_embed


class Factions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="faction", description="Faction management and information")
    async def faction_group(self, inter):
        pass

    @faction_group.sub_command(name="list", description="View all available factions")
    async def faction_list(self, inter: disnake.AppCmdInter):
        """Display all available factions with their bonuses and member counts."""
        db = await get_db()
        
        factions = await db.execute_query(
            "SELECT * FROM factions ORDER BY id"
        )
        
        embed = await create_bot_author_embed(
            title="🏛️ Galactic Factions",
            description="Choose your allegiance and gain powerful bonuses!",
            color=0x9966cc
        )
        
        for faction in factions:
            bonus_text = ""
            if faction['trade_bonus'] > 0:
                bonus_text += f"📈 Trade Bonus: +{faction['trade_bonus']:.1%}\n"
            if faction['jump_bonus'] > 0:
                bonus_text += f"🚀 Jump Success: +{faction['jump_bonus']:.1%}\n"
            if faction['fuel_bonus'] > 0:
                bonus_text += f"⛽ Fuel Efficiency: +{faction['fuel_bonus']:.1%}\n"
            
            if faction['special_ability']:
                bonus_text += f"⭐ Special: {faction['special_ability']}\n"
            
            bonus_text += f"👥 Members: {faction['member_count']:,}"
            
            embed.add_field(
                name=f"🏛️ {faction['name']}",
                value=f"*{faction['description']}*\n\n{bonus_text}",
                inline=False
            )
        
        embed.set_footer(text="Use /faction join <name> to join a faction!")
        
        await send_message(embed=embed, inter=inter)

    @faction_group.sub_command(name="join", description="Join a faction")
    async def faction_join(
        self,
        inter: disnake.AppCmdInter,
        faction_name: str = commands.Param(description="Name of faction to join")
    ):
        """Join a faction to gain bonuses and participate in faction wars."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Check if already in a faction
        if player.faction_id:
            current_faction = await db.execute_query(
                "SELECT name FROM factions WHERE id = $1",
                player.faction_id
            )
            faction_name_current = current_faction[0]['name'] if current_faction else "Unknown"
            
            await send_message(
                msg=f"❌ You're already a member of **{faction_name_current}**! "
                    f"Use `/faction leave` first if you want to switch.",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Find faction
        faction_data = await db.execute_query(
            "SELECT * FROM factions WHERE LOWER(name) = LOWER($1)",
            faction_name
        )
        
        if not faction_data:
            await send_message(
                msg="❌ Faction not found! Use `/faction list` to see available factions.",
                inter=inter,
                ephemeral=True
            )
            return
        
        faction = faction_data[0]
        
        # Join faction
        player.faction_id = faction['id']
        await player.save()
        
        # Update faction member count
        await db.execute_command(
            "UPDATE factions SET member_count = member_count + 1 WHERE id = $1",
            faction['id']
        )
        
        # Check for faction achievement
        await player.check_achievements()
        
        embed = await create_bot_author_embed(
            title="🎉 Faction Joined!",
            description=f"Welcome to **{faction['name']}**!\n\n*{faction['description']}*",
            color=0x00ff00
        )
        
        # Show bonuses
        bonus_text = ""
        if faction['trade_bonus'] > 0:
            bonus_text += f"📈 **Trade Bonus:** +{faction['trade_bonus']:.1%} profit\n"
        if faction['jump_bonus'] > 0:
            bonus_text += f"🚀 **Jump Success:** +{faction['jump_bonus']:.1%} success rate\n"
        if faction['fuel_bonus'] > 0:
            bonus_text += f"⛽ **Fuel Efficiency:** +{faction['fuel_bonus']:.1%} efficiency\n"
        
        if faction['special_ability']:
            bonus_text += f"⭐ **Special Ability:** {faction['special_ability']}\n"
        
        embed.add_field(
            name="🎁 Your New Bonuses",
            value=bonus_text,
            inline=False
        )
        
        embed.add_field(
            name="🏆 Faction Wars",
            value="Participate in weekly faction competitions to earn rewards and glory!",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)

    @faction_group.sub_command(name="leave", description="Leave your current faction")
    async def faction_leave(self, inter: disnake.AppCmdInter):
        """Leave your current faction."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        if not player.faction_id:
            await send_message(
                msg="❌ You're not a member of any faction!",
                inter=inter,
                ephemeral=True
            )
            return
        
        # Get current faction name
        faction_data = await db.execute_query(
            "SELECT name FROM factions WHERE id = $1",
            player.faction_id
        )
        
        faction_name = faction_data[0]['name'] if faction_data else "Unknown"
        
        # Update faction member count
        await db.execute_command(
            "UPDATE factions SET member_count = member_count - 1 WHERE id = $1",
            player.faction_id
        )
        
        # Leave faction
        player.faction_id = None
        await player.save()
        
        embed = await create_bot_author_embed(
            title="👋 Faction Left",
            description=f"You have left **{faction_name}** and are now an independent pilot.\n\n"
                       f"You will no longer receive faction bonuses, but you can join a new faction anytime.",
            color=0xff9900
        )
        
        await send_message(embed=embed, inter=inter)

    @faction_group.sub_command(name="info", description="View detailed faction information")
    async def faction_info(
        self,
        inter: disnake.AppCmdInter,
        faction_name: Optional[str] = commands.Param(default=None, description="Faction to view (default: your faction)")
    ):
        """Display detailed information about a faction."""
        player = await Player.get_or_create(inter.author.id, inter.author.display_name)
        db = await get_db()
        
        # Determine which faction to show
        if faction_name:
            faction_data = await db.execute_query(
                "SELECT * FROM factions WHERE LOWER(name) = LOWER($1)",
                faction_name
            )
            if not faction_data:
                await send_message(
                    msg="❌ Faction not found! Use `/faction list` to see available factions.",
                    inter=inter,
                    ephemeral=True
                )
                return
        else:
            if not player.faction_id:
                await send_message(
                    msg="❌ You're not in a faction! Specify a faction name or join one first.",
                    inter=inter,
                    ephemeral=True
                )
                return
            
            faction_data = await db.execute_query(
                "SELECT * FROM factions WHERE id = $1",
                player.faction_id
            )
        
        faction = faction_data[0]
        is_member = player.faction_id == faction['id']
        
        embed = await create_bot_author_embed(
            title=f"🏛️ {faction['name']}",
            description=faction['description'],
            color=0x9966cc if is_member else 0x666666
        )
        
        # Faction stats
        embed.add_field(
            name="📊 Faction Statistics",
            value=f"**Members:** {faction['member_count']:,}\n"
                  f"**Total Contribution:** {faction['total_contribution']:,} cr\n"
                  f"**Your Status:** {'✅ Member' if is_member else '❌ Not a member'}",
            inline=True
        )
        
        # Bonuses
        bonus_text = ""
        if faction['trade_bonus'] > 0:
            bonus_text += f"📈 **Trade Bonus:** +{faction['trade_bonus']:.1%}\n"
        if faction['jump_bonus'] > 0:
            bonus_text += f"🚀 **Jump Success:** +{faction['jump_bonus']:.1%}\n"
        if faction['fuel_bonus'] > 0:
            bonus_text += f"⛽ **Fuel Efficiency:** +{faction['fuel_bonus']:.1%}\n"
        
        embed.add_field(
            name="🎁 Faction Bonuses",
            value=bonus_text,
            inline=True
        )
        
        if faction['special_ability']:
            embed.add_field(
                name="⭐ Special Ability",
                value=faction['special_ability'],
                inline=False
            )
        
        # Get top contributors
        top_contributors = await db.execute_query(
            """SELECT p.username, 
                      COALESCE(SUM(th.total_value), 0) as contribution
               FROM players p
               LEFT JOIN trade_history th ON p.user_id = th.user_id
               WHERE p.faction_id = $1
               GROUP BY p.user_id, p.username
               ORDER BY contribution DESC
               LIMIT 5""",
            faction['id']
        )
        
        if top_contributors:
            contributor_text = ""
            for i, contributor in enumerate(top_contributors, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                contributor_text += f"{medal} {contributor['username']}: {contributor['contribution']:,} cr\n"
            
            embed.add_field(
                name="🏆 Top Contributors",
                value=contributor_text,
                inline=False
            )
        
        if not is_member:
            embed.set_footer(text=f"Use /faction join {faction['name']} to join this faction!")
        
        await send_message(embed=embed, inter=inter)

    @faction_group.sub_command(name="wars", description="View current faction war status")
    async def faction_wars(self, inter: disnake.AppCmdInter):
        """Display current faction war standings and competition."""
        db = await get_db()
        
        # Get current week's faction war
        current_war = await db.execute_query(
            """SELECT * FROM faction_wars 
               WHERE is_active = true 
               ORDER BY week_start DESC 
               LIMIT 1"""
        )
        
        embed = await create_bot_author_embed(
            title="⚔️ Faction Wars",
            description="Weekly competition between all factions for galactic supremacy!",
            color=0xff6600
        )
        
        if current_war:
            war = current_war[0]
            
            # Get faction standings for current war
            faction_standings = await db.execute_query(
                """SELECT f.name, f.member_count,
                          COALESCE(SUM(th.total_value), 0) as war_contribution,
                          COUNT(DISTINCT th.user_id) as active_members
                   FROM factions f
                   LEFT JOIN players p ON f.id = p.faction_id
                   LEFT JOIN trade_history th ON p.user_id = th.user_id 
                       AND th.timestamp >= $1 
                       AND th.timestamp <= $2
                   GROUP BY f.id, f.name, f.member_count
                   ORDER BY war_contribution DESC""",
                war['week_start'], war['week_end']
            )
            
            embed.add_field(
                name="📅 Current War Period",
                value=f"**Start:** {war['week_start'].strftime('%Y-%m-%d')}\n"
                      f"**End:** {war['week_end'].strftime('%Y-%m-%d')}\n"
                      f"**Participants:** {war['total_participants']:,}",
                inline=True
            )
            
            # Show standings
            standings_text = ""
            for i, faction in enumerate(faction_standings, 1):
                medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                participation_rate = (faction['active_members'] / max(faction['member_count'], 1)) * 100
                
                standings_text += f"{medal} **{faction['name']}**\n"
                standings_text += f"   Contribution: {faction['war_contribution']:,} cr\n"
                standings_text += f"   Participation: {faction['active_members']}/{faction['member_count']} ({participation_rate:.0f}%)\n\n"
            
            embed.add_field(
                name="🏆 Current Standings",
                value=standings_text,
                inline=False
            )
            
        else:
            embed.add_field(
                name="📢 No Active War",
                value="No faction war is currently active. Check back soon for the next competition!",
                inline=False
            )
        
        # Show rewards and rules
        embed.add_field(
            name="🎁 War Rewards",
            value="**1st Place:** 50% bonus to all faction bonuses for one week\n"
                  "**2nd Place:** 25% bonus to all faction bonuses for one week\n"
                  "**3rd Place:** 10% bonus to all faction bonuses for one week\n"
                  "**All Participants:** Achievement progress and recognition",
            inline=False
        )
        
        embed.add_field(
            name="📋 War Rules",
            value="• Contribution is measured by total trade value during the war period\n"
                  "• All faction members can contribute\n"
                  "• Wars run weekly from Monday to Sunday\n"
                  "• Bonuses apply to the following week",
            inline=False
        )
        
        await send_message(embed=embed, inter=inter)


def setup(bot):
    bot.add_cog(Factions(bot))