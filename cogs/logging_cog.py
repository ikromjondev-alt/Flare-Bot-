import discord
from discord import app_commands
from discord.ext import commands

import database as db

log_settings_group = app_commands.Group(name="logsettings", description="Настройка канала логов")

# Эмодзи-значки для типов событий (надёжнее внешних ссылок на картинки — не бьются со временем)
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


@log_settings_group.command(name="channel", description="Указать канал, куда бот будет отправлять логи")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Канал для логов")
async def log_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_log_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Канал логов установлен: {channel.mention}", ephemeral=True)


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

    # ---------- Вступление / выход из сервера ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = self._base_embed("Участник присоединился к серверу", "join", discord.Color.green(), member.display_avatar.url)
        embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
        embed.add_field(name="Аккаунт создан", value=discord.utils.format_dt(member.created_at, style="R"), inline=False)
        await self._log(member.guild, embed)

    # ---------- Сообщения ----------

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = self._base_embed("Сообщение удалено", "msg_delete", discord.Color.red(), message.author.display_avatar.url)
        embed.add_field(name="Автор", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="Канал", value=message.channel.mention, inline=False)
        if message.content:
            embed.add_field(name="Содержимое", value=message.content[:1000], inline=False)
        await self._log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = self._base_embed("Сообщение отредактировано", "msg_edit", discord.Color.orange(), before.author.display_avatar.url)
        embed.add_field(name="Автор", value=f"{before.author.mention} ({before.author.id})", inline=False)
        embed.add_field(name="Канал", value=before.channel.mention, inline=False)
        embed.add_field(name="До", value=(before.content or "—")[:500], inline=False)
        embed.add_field(name="После", value=(after.content or "—")[:500], inline=False)
        await self._log(before.guild, embed)

    # ---------- Голосовые каналы ----------

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild

        if before.channel != after.channel:
            if after.channel and not before.channel:
                embed = self._base_embed("Участник зашёл в голосовой канал", "voice_join", discord.Color.green(), member.display_avatar.url)
                embed.add_field(name="Канал", value=f"🔊 {after.channel.name}\n({after.channel.id})", inline=False)
                embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)
            elif before.channel and not after.channel:
                embed = self._base_embed("Участник вышел из голосового канала", "voice_leave", discord.Color.dark_grey(), member.display_avatar.url)
                embed.add_field(name="Канал", value=f"🔊 {before.channel.name}\n({before.channel.id})", inline=False)
                embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)
            elif before.channel and after.channel:
                embed = self._base_embed("Участник перешёл в другой голосовой канал", "voice_move", discord.Color.blue(), member.display_avatar.url)
                embed.add_field(name="Старый канал", value=f"🔊 {before.channel.name}\n({before.channel.id})", inline=False)
                embed.add_field(name="Новый канал", value=f"🔊 {after.channel.name}\n({after.channel.id})", inline=False)
                embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
                await self._log(guild, embed)

        if before.mute != after.mute:
            state = "выключил" if after.mute else "включил"
            embed = self._base_embed("Серверный микрофон изменён", "voice_mute", discord.Color.orange(), member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
            embed.add_field(name="Действие", value=f"Микрофон **{state}**", inline=False)
            await self._log(guild, embed)

        if before.deaf != after.deaf:
            state = "выключил" if after.deaf else "включил"
            embed = self._base_embed("Серверный звук изменён", "voice_deaf", discord.Color.orange(), member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member.mention}\n({member.id})", inline=False)
            embed.add_field(name="Действие", value=f"Звук **{state}**", inline=False)
            await self._log(guild, embed)

    # ---------- Роли ----------

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = self._base_embed("Роль создана", "role_create", discord.Color.green())
        embed.add_field(name="Роль", value=f"{role.mention}\n({role.id})", inline=False)
        embed.add_field(name="Цвет", value=str(role.color), inline=False)
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = self._base_embed("Роль удалена", "role_delete", discord.Color.red())
        embed.add_field(name="Роль", value=f"**{role.name}**\n({role.id})", inline=False)
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        if before.name != after.name:
            changes.append(("Название", f"{before.name} → {after.name}"))
        if before.color != after.color:
            changes.append(("Цвет", f"`{str(before.color).upper()}` → `{str(after.color).upper()}`"))
        if before.permissions != after.permissions:
            changes.append(("Права", "изменены права роли"))
        if before.hoist != after.hoist:
            changes.append(("Отдельный список", f"{before.hoist} → {after.hoist}"))
        if before.mentionable != after.mentionable:
            changes.append(("Упоминаемость", f"{before.mentionable} → {after.mentionable}"))
        if not changes:
            return
        embed = self._base_embed("Роль изменена", "role_update", discord.Color.orange())
        embed.add_field(name="Роль", value=f"{after.mention}\n({after.id})", inline=False)
        for name, value in changes:
            embed.add_field(name=name, value=value, inline=False)
        await self._log(after.guild, embed)

    # ---------- Каналы ----------

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = self._base_embed("Канал создан", "channel_create", discord.Color.green())
        embed.add_field(name="Канал", value=f"{channel.mention if hasattr(channel, 'mention') else channel.name}\n({channel.id})", inline=False)
        embed.add_field(name="Тип", value=str(channel.type), inline=False)
        if getattr(channel, "category", None):
            embed.add_field(name="Категория", value=channel.category.name, inline=False)
        await self._log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = self._base_embed("Канал удалён", "channel_delete", discord.Color.red())
        embed.add_field(name="Канал", value=f"**{channel.name}**\n({channel.id})", inline=False)
        embed.add_field(name="Тип", value=str(channel.type), inline=False)
        await self._log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        changes = []
        if before.name != after.name:
            changes.append(("Название", f"{before.name} → {after.name}"))
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic:
                changes.append(("Тема", f"{before.topic or '—'} → {after.topic or '—'}"))
            if before.slowmode_delay != after.slowmode_delay:
                changes.append(("Медленный режим", f"{before.slowmode_delay}с → {after.slowmode_delay}с"))
        if not changes:
            return
        embed = self._base_embed("Канал изменён", "channel_update", discord.Color.orange())
        embed.add_field(name="Канал", value=f"{after.mention if hasattr(after, 'mention') else after.name}\n({after.id})", inline=False)
        for name, value in changes:
            embed.add_field(name=name, value=value, inline=False)
        await self._log(after.guild, embed)

    # ---------- Ручные действия модераторов через сам Discord (не через бота) ----------
    # Используем Audit Log API, чтобы отличить: кто именно и почему забанил/кикнул/
    # выдал роль напрямую через интерфейс Discord, минуя команды бота.

    async def _get_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and getattr(entry.target, "id", None) == target_id:
                    return entry
        except discord.Forbidden:
            return None
        return None

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await self._get_audit_entry(guild, discord.AuditLogAction.ban, user.id)
        embed = self._base_embed("Участник забанен (через Discord)", "role_delete", discord.Color.red(), user.display_avatar.url)
        embed.add_field(name="Пользователь", value=f"{user} ({user.id})", inline=False)
        if entry:
            embed.add_field(name="Модератор", value=f"{entry.user.mention} ({entry.user.id})", inline=False)
            embed.add_field(name="Причина", value=entry.reason or "—", inline=False)
        await self._log(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        entry = await self._get_audit_entry(guild, discord.AuditLogAction.unban, user.id)
        embed = self._base_embed("Участник разбанен (через Discord)", "role_create", discord.Color.green(), user.display_avatar.url)
        embed.add_field(name="Пользователь", value=f"{user} ({user.id})", inline=False)
        if entry:
            embed.add_field(name="Модератор", value=f"{entry.user.mention} ({entry.user.id})", inline=False)
        await self._log(guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        # Изменение ролей вручную (не через бота — бот сам не шлёт этого события отдельно,
        # поэтому для действий бота эта проверка не создаёт дублей: наши команды выше уже
        # логируют события напрямую с полным контекстом, а здесь только сверяем список ролей)
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added = after_roles - before_roles
        removed = before_roles - after_roles
        if added or removed:
            action = discord.AuditLogAction.member_role_update
            entry = await self._get_audit_entry(guild, action, after.id)
            embed = self._base_embed("Роли участника изменены", "role_update", discord.Color.orange(), after.display_avatar.url)
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            if added:
                embed.add_field(name="Роли выданы", value=", ".join(r.mention for r in added), inline=False)
            if removed:
                embed.add_field(name="Роли сняты", value=", ".join(r.mention for r in removed), inline=False)
            if entry and entry.user:
                embed.add_field(name="Кем изменено", value=f"{entry.user.mention}", inline=False)
            await self._log(guild, embed)

        # Изменение ника администратором
        if before.nick != after.nick:
            entry = await self._get_audit_entry(guild, discord.AuditLogAction.member_update, after.id)
            embed = self._base_embed("Никнейм изменён", "channel_update", discord.Color.orange(), after.display_avatar.url)
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            embed.add_field(name="Было", value=before.nick or before.name, inline=False)
            embed.add_field(name="Стало", value=after.nick or after.name, inline=False)
            if entry and entry.user and entry.user.id != after.id:
                embed.add_field(name="Кем изменено", value=f"{entry.user.mention}", inline=False)
            await self._log(guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Проверяем, не был ли это кик (а не добровольный выход) — через Audit Log
        entry = await self._get_audit_entry(member.guild, discord.AuditLogAction.kick, member.id)
        if entry:
            embed = self._base_embed("Участник кикнут (через Discord)", "leave", discord.Color.orange(), member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
            embed.add_field(name="Модератор", value=f"{entry.user.mention} ({entry.user.id})", inline=False)
            embed.add_field(name="Причина", value=entry.reason or "—", inline=False)
        else:
            embed = self._base_embed("Участник покинул сервер", "leave", discord.Color.dark_grey(), member.display_avatar.url)
            embed.add_field(name="Участник", value=f"{member} ({member.id})", inline=False)
        await self._log(member.guild, embed)


async def setup(bot: commands.Bot):
    bot.tree.add_command(log_settings_group)
    await bot.add_cog(LoggingCog(bot))
