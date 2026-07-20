import discord
from discord import app_commands
from discord.ext import commands

import config
from i18n import t


@app_commands.command(name="support", description="How to contact support")
async def support(interaction: discord.Interaction):
    embed = discord.Embed(
        title=await t(interaction.guild_id, "support.title"),
        description=await t(interaction.guild_id, "support.desc", username=config.SUPPORT_USERNAME),
        color=discord.Color.blurple(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


class Support(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(support)
    await bot.add_cog(Support(bot))
