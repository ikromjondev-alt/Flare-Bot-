import discord
from discord import app_commands
from discord.ext import commands

import database as db


@app_commands.command(name="language", description="Change bot language")
@app_commands.describe(lang="ru — Russian, en — English")
@app_commands.choices(lang=[
    app_commands.Choice(name="Русский", value="ru"),
    app_commands.Choice(name="English", value="en"),
])
@app_commands.checks.has_permissions(administrator=True)
async def language_cmd(interaction: discord.Interaction, lang: app_commands.Choice[str]):
    await db.set_language(interaction.guild_id, lang.value)
    label = "Русский" if lang.value == "ru" else "English"
    await interaction.response.send_message(f"✅ Language set to: **{label}**", ephemeral=True)


class Language(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(language_cmd)
    await bot.add_cog(Language(bot))
