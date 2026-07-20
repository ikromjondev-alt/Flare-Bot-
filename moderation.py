import re
import time as time_module

import discord
from discord import app_commands
from discord.ext import commands, tasks

import database as db
from i18n import t

TIME_RE = re.compile(r"^(\d+)\s*(d|day|days|день|дня|дней|m|min|minute|minutes|минута|минуты|минут)$", re.IGNORECASE)


def parse_duration(text: str) -> int | None:
    """Parse duration string to seconds. None = permanent."""
    if not text or text.strip().lower() in ("perm", "permanent", "навсегда", "-"):
        return None
    match = TIME_RE.match(text.strip())
    if not match:
        raise ValueError("Invalid time format. Use: 3d, 30m, 2 days, 15 minutes.")
    amount = int(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("d") or "день" in unit or "дня" in unit or "дней" in unit:
        return amount * 86400
    return amount * 60


def has_mod_permissions():
    async def predicate(interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        return perms.moderate_members or perms.administrator
    return app_commands.check(predicate)


async def get_or_create_mute_role(guild: discord.Guild) -> discord.Role:
    role_id = await db.get_mute_role(guild.id)
    role = guild.get_role(role_id) if role_id else None
    if role is None:
        role = discord.utils.get(guild.roles, name="Muted")
    if role is None:
        role = await guild.create_role(name="Muted", reason="Auto-created mute role")
        for channel in guild.channels:
            try:
                await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            except discord.Forbidden:
                pass
    await db.set_mute_role(guild.id, role.id)
    return role


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_mutes.start()
        self.check_bans.start()

    def cog_unload(self):
        self.check_mutes.cancel()
        self.check_bans.cancel()

    @tasks.loop(seconds=60)
    async def check_mutes(self):
        now = int(time_module.time())
        rows = await db.get_active_mutes()
        for guild_id, user_id, expires_at in rows:
            if expires_at is not None and expires_at <= now:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue
                member = guild.get_member(user_id)
                await db.remove_mute(guild_id, user_id)
                if member:
                    role = await get_or_create_mute_role(guild)
                    try:
                        await member.remove_roles(role, reason="Mute expired")
                    except discord.Forbidden:
                        pass

    @check_mutes.before_loop
    async def before_check_mutes(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=60)
    async def check_bans(self):
        now = int(time_module.time())
        rows = await db.get_active_bans()
        for guild_id, user_id, expires_at in rows:
            if expires_at is not None and expires_at <= now:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue
                await db.remove_ban(guild_id, user_id)
                try:
                    await guild.unban(discord.Object(id=user_id), reason="Ban expired")
                except (discord.NotFound, discord.Forbidden):
                    pass

    @check_bans.before_loop
    async def before_check_bans(self):
        await self.bot.wait_until_ready()

    # ---------- MUTE ----------

    @app_commands.command(name="mute", description="Mute a member for a specified time")
    @app_commands.describe(
        member="Member to mute",
        reason="Reason for mute",
        time="Duration (e.g. 3d, 30m). Leave empty for permanent",
    )
    @has_mod_permissions()
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: str, time: str = ""):
        try:
            duration = parse_duration(time)
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        role = await get_or_create_mute_role(interaction.guild)
        try:
            await member.add_roles(role, reason=f"Muted by {interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don\'t have permission to assign roles.", ephemeral=True)
            return

        expires_at = (int(time_module.time()) + duration) if duration else None
        await db.add_mute(interaction.guild_id, member.id, interaction.user.id, reason, expires_at)

        duration_text = time if duration else await t(interaction.guild_id, "mod.mute.forever")
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.mute.title"),
            color=discord.Color.orange(),
            description=await t(
                interaction.guild_id, "mod.mute.desc",
                member=member.mention, duration=duration_text, reason=reason,
            ),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="Member to unmute", reason="Reason")
    @has_mod_permissions()
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "not specified"):
        role = await get_or_create_mute_role(interaction.guild)
        try:
            await member.remove_roles(role, reason=f"Unmuted by {interaction.user}: {reason}")
        except discord.Forbidden:
            pass
        await db.remove_mute(interaction.guild_id, member.id)
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unmute.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unmute.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- WARN ----------

    @app_commands.command(name="warn", description="Issue a warning to a member")
    @app_commands.describe(member="Member to warn", reason="Reason")
    @has_mod_permissions()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        await db.add_warn(interaction.guild_id, member.id, interaction.user.id, reason)
        warns = await db.get_warns(interaction.guild_id, member.id)
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.warn.title"),
            color=discord.Color.yellow(),
            description=await t(
                interaction.guild_id, "mod.warn.desc",
                member=member.mention, reason=reason, count=len(warns),
            ),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unwarn", description="Remove the last warning from a member")
    @app_commands.describe(member="Member to remove warning from", reason="Reason")
    @has_mod_permissions()
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "not specified"):
        removed = await db.remove_last_warn(interaction.guild_id, member.id)
        if not removed:
            await interaction.response.send_message(
                await t(interaction.guild_id, "mod.unwarn.none"), ephemeral=True
            )
            return
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unwarn.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unwarn.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- BAN ----------

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(
        member="Member to ban",
        reason="Reason for ban",
        days="Duration in days (leave empty or 0 for permanent)",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str, days: int = 0):
        try:
            await member.ban(reason=f"{interaction.user}: {reason}", delete_message_seconds=0)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Not enough permissions to ban.", ephemeral=True)
            return

        duration_text = await t(interaction.guild_id, "mod.ban.days", days=days) if days else await t(interaction.guild_id, "mod.mute.forever")
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.ban.title"),
            color=discord.Color.red(),
            description=await t(
                interaction.guild_id, "mod.ban.desc",
                member=member.mention, duration=duration_text, reason=reason,
            ),
        )
        await interaction.response.send_message(embed=embed)

        if days and days > 0:
            expires_at = int(time_module.time()) + (days * 86400)
            await db.add_ban(interaction.guild_id, member.id, interaction.user.id, reason, expires_at)
        else:
            await db.add_ban(interaction.guild_id, member.id, interaction.user.id, reason, None)

    @app_commands.command(name="unban", description="Unban a user by username or ID")
    @app_commands.describe(username="Username or user ID", reason="Reason")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, username: str, reason: str = "not specified"):
        bans = [entry async for entry in interaction.guild.bans()]
        target = None
        for entry in bans:
            if str(entry.user.id) == username or entry.user.name.lower() == username.lower():
                target = entry.user
                break
        if target is None:
            await interaction.response.send_message(
                await t(interaction.guild_id, "mod.unban.notfound"), ephemeral=True
            )
            return
        await interaction.guild.unban(target, reason=f"{interaction.user}: {reason}")
        await db.remove_ban(interaction.guild_id, target.id)
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unban.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unban.desc", user=str(target), reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- KICK ----------

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="Member to kick", reason="Reason")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        try:
            await member.kick(reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Not enough permissions to kick.", ephemeral=True)
            return
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.kick.title"),
            color=discord.Color.orange(),
            description=await t(interaction.guild_id, "mod.kick.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                await t(interaction.guild_id, "mod.noperm"), ephemeral=True
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
