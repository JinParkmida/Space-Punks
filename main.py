import asyncio
import tracemalloc

import disnake
from disnake.ext import commands
from keys import get_keys
from models import Bot

DEV_MODE = True


if __name__ == "__main__":
    tracemalloc.start()
    intents = disnake.Intents.default()
    intents.members = True  # turn on privileged members intent
    intents.messages = True
    intents.message_content = True
    
    t_keys = get_keys()

    options = {
        "case_insensitive": True,
        "owner_id": t_keys.bot_owner_id,
        "intents": intents,
        "test_guilds": None if not DEV_MODE else [t_keys.support_server_id],
        "command_sync_flags": commands.CommandSyncFlags.all(),
        "chunk_guilds_at_startup": DEV_MODE
    }
    loop = asyncio.get_event_loop()

    bot = Bot(t_keys.bot_prefix, t_keys, dev_mode=DEV_MODE, **options)

    try:
        loop.run_until_complete(bot.start(
            t_keys.prod_bot_token if not DEV_MODE else t_keys.dev_bot_token
        ))
    except KeyboardInterrupt:
        # cancel all tasks lingering.
        loop.run_until_complete(bot.close())
    finally:
        tracemalloc.stop()