import discord
from discord import app_commands
from discord.ext import commands

import database as db


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


@app_commands.command(name="autorole", description="Настроить авто-выдачу роли новым участникам и приветствие")
@app_commands.describe(
    channel="Канал, куда будут отправляться приветствия",
    role="Роль, которая будет выдаваться автоматически",
    message="Кастомное сообщение в приветствии (необязательно)",
)
@is_admin()
async def autorole_cmd(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role,
    message: str = "",
):
    await db.set_autorole_channel(interaction.guild_id, channel.id)
    await db.set_autorole_role(interaction.guild_id, role.id)
    if message:
        await db.set_autorole_message(interaction.guild_id, message)
    await db.set_autorole_enabled(interaction.guild_id, True)  # включается сразу, без отдельной команды

    embed = discord.Embed(
        title="✅ Авто-выдача роли настроена и включена",
        color=discord.Color.green(),
    )
    embed.add_field(name="Канал приветствий", value=channel.mention, inline=False)
    embed.add_field(name="Роль", value=role.mention, inline=False)
    if message:
        embed.add_field(name="Кастомное сообщение", value=message, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(name="autorole_off", description="Выключить авто-выдачу роли новым участникам")
@is_admin()
async def autorole_off_cmd(interaction: discord.Interaction):
    await db.set_autorole_enabled(interaction.guild_id, False)
    await interaction.response.send_message("✅ Авто-выдача роли выключена.", ephemeral=True)


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(autorole_cmd)
    bot.tree.add_command(autorole_off_cmd)
    await bot.add_cog(AutoRole(bot))
