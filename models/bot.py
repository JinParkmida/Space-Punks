import asyncio
from typing import List

import aiohttp
from disnake.ext.commands import AutoShardedBot, errors
from disnake import ApplicationCommandInteraction as AppCmdInter

from cogs import cogs_list
from datetime import datetime
from util import logger
from models.database import db_manager
import disnake


class Bot(AutoShardedBot):
    def __init__(self, default_bot_prefix, keys, dev_mode=False, **settings):
        super(Bot, self).__init__(self.prefix_check, **settings)
        self.default_prefix = default_bot_prefix
        self.keys = keys
        
        # Load game cogs
        for cog in cogs_list:
            self.load_extension(f"cogs.{cog}")

        self.dev_mode = dev_mode
        self.logger = logger
        self.http_session = aiohttp.ClientSession()

    async def prefix_check(
        self, bot: AutoShardedBot, msg: disnake.Message
    ) -> List[str]:
        """Get a list of prefixes for a Guild."""
        return [self.default_prefix]

    async def on_ready(self):
        # Initialize database connection
        await db_manager.initialize()
        
        msg = (
            f"{self.keys.bot_name} is now ready at {datetime.now()}.\n"
            f"🌌 Star Trading RPG Bot is active! 🚀\n"
            f"Database connected and ready for galactic commerce!"
        )
        print(msg)
        logger.info(msg)

    async def close(self):
        """Clean shutdown of bot and database connections."""
        await db_manager.close()
        await self.http_session.close()
        await super().close()

    async def on_slash_command_error(
        self, interaction: AppCmdInter, exception: errors.CommandError
    ) -> None:
        inter = interaction
        
        if isinstance(exception, errors.NotOwner):
            error_message = "Only the bot owner can use this command."
        elif isinstance(exception, errors.CheckFailure):
            error_message = str(exception)
        else:
            logger.error(f"Slash command error: {exception}")
            error_message = "An error occurred while processing your command. Please try again."

        if error_message:
            try:
                await inter.send(error_message, ephemeral=True)
            except:
                # If interaction already responded, try followup
                try:
                    await inter.followup.send(error_message, ephemeral=True)
                except:
                    logger.error("Failed to send error message to user")

    async def on_command_error(self, context, exception):
        return_error_to_user = [
            errors.BotMissingPermissions,
            errors.BadArgument,
            errors.MemberNotFound,
            errors.UserNotFound,
            errors.EmojiNotFound,
        ]
        
        if isinstance(exception, errors.CommandNotFound):
            return
        elif isinstance(exception, errors.CommandInvokeError):
            logger.error(f"Command invoke error: {exception}")
            try:
                if exception.original.status == 403:
                    return
            except AttributeError:
                return
            return await context.send(f"An error occurred: {exception}")
        if any(isinstance(exception, error) for error in return_error_to_user):
            return await context.send(f"{exception}")
        else:
            logger.error(f"Unhandled command error: {exception}")

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def on_message_edit(self, before, after):
        await self.on_message(after)