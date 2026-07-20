import discord
from discord import app_commands
from discord.ext import commands

import database as db

log_settings_group = app_commands.Group(name="logsettings", description="Log channel settings")

ICONS = {
    "join": "📥",
    "leave": "📤",
    "voice_join": "🔊",
    "voice_leave": "🔇",
    "voice_move": "🔀",
    "voice_mute": "🎙️",
    "voice_deaf": "🎧",
    "msg_delete": "🗑️",
    "msg_edit": "✏️",
    "role_create": "➕",
    "role_delete": "➖",
    "role_update": "🎨",
    "channel_create": "📁",
    "channel_delete": "🗑️",
    "channel_update": "⚙️",
}


@log_settings_group.command(name="channel", description="Set log channel")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Channel for logs")
async def log_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_log_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Log channel set: {channel.mention}", ephemeral=True)


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        channel_id = await db.get_log_channel(guild.id)
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    def _base_embed(self, event_title: str, icon_key: str, color: discord.Color, thumbnail_url: str | None = None):
        icon = ICONS.get(icon_key, "")
        embed = discord.Embed(title=f"{icon} {event_title}", color=color, timestamp=discord.utils.utcnow())
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        return embed

    # Member join/leave
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self._base_embed("Member joined", "join", discord.Color.green(), member.display_avatar.url)
        embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, style="R"), inline=False)
        await self._log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = self._base_embed("Member left", "leave", discord.Color.dark_grey(), member.display_avatar.url)
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=False)
        await self._log(member.guild, embed)

    # Messages
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = self._base_embed("Message deleted", "msg_delete", discord.Color.red(), message.author.display_avatar.url)
        embed.add_field(name="Author", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        if message.content:
            embed.add_field(name="Content", value=message.content[:1000], inline=False)
        await self._log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        if not after.content:
            return
        embed = self._base_embed("Message edited", "msg_edit", discord.Color.orange(), before.author.display_avatar.url)
        embed.add_field(name="Author", value=f"{before.author.mention} ({before.author.id})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Before", value=(before.content or "—")[:500], inline=False)
        embed.add_field(name="After", value=(after.content or "—")[:500], inline=False)
        await self._log(before.guild, embed)

    # Voice
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild

        if before.channel != after.channel:
            if after.channel and not before.channel:
                embed = self._base_embed("Joined voice channel", "voice_join", discord.Color.green(), member.display_avatar.url)
                embed.add_field(name="Channel", value=f"🔊 {after.channel.name}\n({after.channel.id})", inline=False)
                embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)
            elif before.channel and not after.channel:
                embed = self._base_embed("Left voice channel", "voice_leave", discord.Color.dark_grey(), member.display_avatar.url)
                embed.add_field(name="Channel", value=f"🔊 {before.channel.name}\n({before.channel.id})", inline=False)
                embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)
            elif before.channel and after.channel:
                embed = self._base_embed("Moved voice channel", "voice_move", discord.Color.blue(), member.display_avatar.url)
                embed.add_field(name="Old channel", value=f"🔊 {before.channel.name}\n({before.channel.id})", inline=False)
                embed.add_field(name="New channel", value=f"🔊 {after.channel.name}\n({after.channel.id})", inline=False)
                embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)

        if before.mute != after.mute:
            state = "muted" if after.mute else "unmuted"
            embed = self._base_embed("Server mute changed", "voice_mute", discord.Color.orange(), member.display_avatar.url)
            embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
            embed.add_field(name="Action", value=f"Microphone **{state}**", inline=False)
            await self._log(guild, embed)

        if before.deaf != after.deaf:
            state = "deafened" if after.deaf else "undeafened"
            embed = self._base_embed("Server deafen changed", "voice_deaf", discord.Color.orange(), member.display_avatar.url)
            embed.add_field(name="Member", value=f"{member.mention}\n({member.id})", inline=False)
            embed.add_field(name="Action", value=f"Sound **{state}**", inline=False)
            await self._log(guild, embed)

    # Roles
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = self._base_embed("Role created", "role_create", discord.Color.green())
        embed.add_field(name="Role", value=f"{role.mention}\n({role.id})", inline=False)
        embed.add_field(name="Color", value=str(role.color), inline=False)
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = self._base_embed("Role deleted", "role_delete", discord.Color.red())
        embed.add_field(name="Role", value=f"**{role.name}**\n({role.id})", inline=False)
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        if before.name != after.name:
            changes.append(("Name", f"{before.name} → {after.name}"))
        if before.color != after.color:
            changes.append(("Color", f"`{str(before.color).upper()}` → `{str(after.color).upper()}`"))
        if before.permissions != after.permissions:
            changes.append(("Permissions", "role permissions changed"))
        if before.hoist != after.hoist:
            changes.append(("Hoist", f"{before.hoist} → {after.hoist}"))
        if before.mentionable != after.mentionable:
            changes.append(("Mentionable", f"{before.mentionable} → {after.mentionable}"))
        if not changes:
            return
        embed = self._base_embed("Role updated", "role_update", discord.Color.orange())
        embed.add_field(name="Role", value=f"{after.mention}\n({after.id})", inline=False)
        for name, value in changes:
            embed.add_field(name=name, value=value, inline=False)
        await self._log(after.guild, embed)

    # Channels
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self._base_embed("Channel created", "channel_create", discord.Color.green())
        embed.add_field(name="Channel", value=f"{channel.mention if hasattr(channel, 'mention') else channel.name}\n({channel.id})", inline=False)
        embed.add_field(name="Type", value=str(channel.type), inline=False)
        if getattr(channel, "category", None):
            embed.add_field(name="Category", value=channel.category.name, inline=False)
        await self._log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self._base_embed("Channel deleted", "channel_delete", discord.Color.red())
        embed.add_field(name="Channel", value=f"**{channel.name}**\n({channel.id})", inline=False)
        embed.add_field(name="Type", value=str(channel.type), inline=False)
        await self._log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        changes = []
        if before.name != after.name:
            changes.append(("Name", f"{before.name} → {after.name}"))
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic:
                changes.append(("Topic", f"{before.topic or '—'} → {after.topic or '—'}"))
            if before.slowmode_delay != after.slowmode_delay:
                changes.append(("Slowmode", f"{before.slowmode_delay}s → {after.slowmode_delay}s"))
        if not changes:
            return
        embed = self._base_embed("Channel updated", "channel_update", discord.Color.orange())
        embed.add_field(name="Channel", value=f"{after.mention if hasattr(after, 'mention') else after.name}\n({after.id})", inline=False)
        for name, value in changes:
            embed.add_field(name=name, value=value, inline=False)
        await self._log(after.guild, embed)


async def setup(bot: commands.Bot):
    bot.tree.add_command(log_settings_group)
    await bot.add_cog(LoggingCog(bot))
