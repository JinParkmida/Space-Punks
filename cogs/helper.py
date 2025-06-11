from typing import Optional, Union, List
import disnake
from disnake.ext import commands
from util import logger


async def send_message(
    *custom_args,
    msg: str = None,
    ctx: commands.Context = None,
    inter: disnake.AppCmdInter = None,
    channel: disnake.TextChannel = None,
    allowed_mentions: disnake.AllowedMentions = None,
    view: disnake.ui.View = None,
    delete_after: int = None,
    embed: Optional[disnake.Embed] = None,
    embeds: Optional[List[disnake.Embed]] = None,
    ephemeral: bool = False,
):
    """Send a message to a discord channel/interaction."""
    
    if not msg and not embed and not embeds:
        logger.error("No message content to send")
        return

    if msg:
        msg = msg.replace("\\n", "\n")

    final_msgs = []
    
    if ctx:
        final_msgs.append(
            await ctx.send(
                msg,
                allowed_mentions=allowed_mentions,
                view=view,
                delete_after=delete_after,
                embed=embed,
                embeds=embeds,
            )
        )
    
    if channel:
        final_msgs.append(
            await channel.send(
                msg,
                allowed_mentions=allowed_mentions,
                view=view,
                delete_after=delete_after,
                embed=embed,
                embeds=embeds,
            )
        )
    
    if inter:
        if not view:
            view = disnake.utils.MISSING
        if not allowed_mentions:
            allowed_mentions = disnake.utils.MISSING
        if not delete_after:
            delete_after = disnake.utils.MISSING
        if not embed:
            embed = disnake.utils.MISSING
        if not embeds:
            embeds = disnake.utils.MISSING
            
        final_msgs.append(
            await inter.send(
                msg,
                allowed_mentions=allowed_mentions,
                view=view,
                delete_after=delete_after,
                embed=embed,
                embeds=embeds,
                ephemeral=ephemeral,
            )
        )

    return final_msgs