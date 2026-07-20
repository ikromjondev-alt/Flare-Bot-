import discord
from discord import app_commands
from discord.ext import commands

import database as db


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


autorole_group = app_commands.Group(
    name="autorole", description="Настройка авто-выдачи ролей и приветственного канала"
)


@autorole_group.command(name="setup", description="Шаг 1: Начать настройку авто-роли")
@is_admin()
async def autorole_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Настройка авто-выдачи ролей",
        description=(
            "Пройдите шаги настройки командами:\n\n"
            "**Шаг 2** — `/autorole channel` — выбрать канал приветствий\n"
            "**Шаг 3** — `/autorole role` — выбрать роль для авто-выдачи\n"
            "**Шаг 4** — `/autorole message` — кастомное сообщение (необязательно)\n\n"
            "После этого включите функцию командой `/autorole enable`.\n"
            "Без участия администратора бот сам выдаст выбранную роль каждому новому участнику."
        ),
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@autorole_group.command(name="channel", description="Шаг 2: Выбрать канал для приветственных сообщений")
@is_admin()
@app_commands.describe(channel="Канал, куда будут отправляться приветствия")
async def autorole_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_autorole_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Канал приветствий установлен: {channel.mention}", ephemeral=True)


@autorole_group.command(name="role", description="Шаг 3: Выбрать роль, которая будет выдаваться автоматически")
@is_admin()
@app_commands.describe(role="Роль для авто-выдачи новым участникам")
async def autorole_role(interaction: discord.Interaction, role: discord.Role):
    await db.set_autorole_role(interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ Роль для авто-выдачи установлена: {role.mention}", ephemeral=True)


@autorole_group.command(name="message", description="Шаг 4 (необязательно): Задать кастомное приветственное сообщение")
@is_admin()
@app_commands.describe(text="Текст, который будет добавлен в приветственное сообщение")
async def autorole_message(interaction: discord.Interaction, text: str):
    await db.set_autorole_message(interaction.guild_id, text)
    await interaction.response.send_message("✅ Кастомное сообщение сохранено.", ephemeral=True)


@autorole_group.command(name="enable", description="Включить авто-выдачу роли новым участникам")
@is_admin()
async def autorole_enable(interaction: discord.Interaction):
    cfg = await db.get_autorole_config(interaction.guild_id)
    if not cfg or not cfg[1]:
        await interaction.response.send_message(
            "⚠️ Сначала укажите роль через `/autorole role`.", ephemeral=True
        )
        return
    await db.set_autorole_enabled(interaction.guild_id, True)
    await interaction.response.send_message("✅ Авто-выдача роли включена.", ephemeral=True)


@autorole_group.command(name="disable", description="Отключить авто-выдачу роли новым участникам")
@is_admin()
async def autorole_disable(interaction: discord.Interaction):
    await db.set_autorole_enabled(interaction.guild_id, False)
    await interaction.response.send_message("✅ Авто-выдача роли отключена.", ephemeral=True)


@autorole_group.command(name="status", description="Показать текущие настройки авто-роли")
@is_admin()
async def autorole_status(interaction: discord.Interaction):
    cfg = await db.get_autorole_config(interaction.guild_id)
    if not cfg:
        await interaction.response.send_message("Настройки ещё не заданы.", ephemeral=True)
        return
    channel_id, role_id, custom_message, enabled = cfg
    channel = interaction.guild.get_channel(channel_id) if channel_id else None
    role = interaction.guild.get_role(role_id) if role_id else None
    embed = discord.Embed(title="📋 Текущие настройки авто-роли", color=discord.Color.blurple())
    embed.add_field(name="Канал приветствий", value=channel.mention if channel else "не задан", inline=False)
    embed.add_field(name="Роль", value=role.mention if role else "не задана", inline=False)
    embed.add_field(name="Кастомное сообщение", value=custom_message or "—", inline=False)
    embed.add_field(name="Статус", value="🟢 включено" if enabled else "🔴 выключено", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(autorole_group)
    await bot.add_cog(AutoRole(bot))
