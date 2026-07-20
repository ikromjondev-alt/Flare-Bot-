import asyncio
import logging

import discord
from discord.ext import commands

import config
from database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("bot")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.voice_states = True


class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS, help_command=None)

    async def setup_hook(self):
        await init_db()
        log.info("Database initialized.")

        extensions = [
            "cogs.welcome",
            "cogs.moderation",
            "cogs.autorole",
            "cogs.report",
            "cogs.support",
            "cogs.help_cmd",
            "cogs.logging_cog",
            "cogs.antispam",
            "cogs.language",
            "cogs.webapp",
        ]
        for ext in extensions:
            await self.load_extension(ext)
            log.info(f"Loaded extension: {ext}")

        if config.GUILD_ID:
            guild = discord.Object(id=int(config.GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info(f"Synced {len(synced)} commands on guild {config.GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            log.info(f"Synced {len(synced)} commands globally (may take up to 1 hour).")

    async def on_ready(self):
        log.info(f"Bot started as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help"))


async def main():
    if not config.TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set — fill .env file (see .env.example).")
    bot = ModBot()
    async with bot:
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
