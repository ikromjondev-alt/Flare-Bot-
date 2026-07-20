import discord
from discord import app_commands
from discord.ext import commands

import database as db


def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


autorole_group = app_commands.Group(
    name="autorole", description="Auto-role and welcome channel setup"
)


@autorole_group.command(name="setup", description="Step 1: Start auto-role setup")
@is_admin()
async def autorole_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Auto-Role Setup",
        description=(
            "Follow the setup steps:\n\n"
            "**Step 2** — `/autorole channel` — select welcome channel\n"
            "**Step 3** — `/autorole role` — select auto-role\n"
            "**Step 4** — `/autorole message` — custom message (optional)\n\n"
            "Then enable with `/autorole enable`.\n"
            "Bot will automatically assign the selected role to new members."
        ),
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@autorole_group.command(name="channel", description="Step 2: Select welcome channel")
@is_admin()
@app_commands.describe(channel="Channel for welcome messages")
async def autorole_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_autorole_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Welcome channel set: {channel.mention}", ephemeral=True)


@autorole_group.command(name="role", description="Step 3: Select auto-role")
@is_admin()
@app_commands.describe(role="Role to auto-assign to new members")
async def autorole_role(interaction: discord.Interaction, role: discord.Role):
    await db.set_autorole_role(interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ Auto-role set: {role.mention}", ephemeral=True)


@autorole_group.command(name="message", description="Step 4 (optional): Set custom welcome message")
@is_admin()
@app_commands.describe(text="Custom text added to welcome message")
async def autorole_message(interaction: discord.Interaction, text: str):
    await db.set_autorole_message(interaction.guild_id, text)
    await interaction.response.send_message("✅ Custom message saved.", ephemeral=True)


@autorole_group.command(name="enable", description="Enable auto-role")
@is_admin()
async def autorole_enable(interaction: discord.Interaction):
    cfg = await db.get_autorole_config(interaction.guild_id)
    if not cfg or not cfg[1]:
        await interaction.response.send_message(
            "⚠️ Set a role first via `/autorole role`.", ephemeral=True
        )
        return
    await db.set_autorole_enabled(interaction.guild_id, True)
    await interaction.response.send_message("✅ Auto-role enabled.", ephemeral=True)


@autorole_group.command(name="disable", description="Disable auto-role")
@is_admin()
async def autorole_disable(interaction: discord.Interaction):
    await db.set_autorole_enabled(interaction.guild_id, False)
    await interaction.response.send_message("✅ Auto-role disabled.", ephemeral=True)


@autorole_group.command(name="status", description="Show current auto-role settings")
@is_admin()
async def autorole_status(interaction: discord.Interaction):
    cfg = await db.get_autorole_config(interaction.guild_id)
    if not cfg:
        await interaction.response.send_message("Settings not configured yet.", ephemeral=True)
        return
    channel_id, role_id, custom_message, enabled = cfg
    channel = interaction.guild.get_channel(channel_id) if channel_id else None
    role = interaction.guild.get_role(role_id) if role_id else None
    embed = discord.Embed(title="📋 Auto-Role Settings", color=discord.Color.blurple())
    embed.add_field(name="Welcome channel", value=channel.mention if channel else "not set", inline=False)
    embed.add_field(name="Role", value=role.mention if role else "not set", inline=False)
    embed.add_field(name="Custom message", value=custom_message or "—", inline=False)
    embed.add_field(name="Status", value="🟢 enabled" if enabled else "🔴 disabled", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(autorole_group)
    await bot.add_cog(AutoRole(bot))
