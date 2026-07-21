import re
import asyncio
import datetime

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from i18n import t

TIME_RE = re.compile(r"^(\d+)\s*(d|day|days|день|дня|дней|m|min|minute|minutes|минута|минуты|минут)$", re.IGNORECASE)

# Discord ограничивает встроенный timeout максимум 28 днями — это лимит самого API, не наш
MAX_TIMEOUT_SECONDS = 28 * 86400
WARN_TIMEOUT_SECONDS = 4 * 3600  # /warn всегда даёт тайм-аут на 4 часа


def parse_duration(text: str) -> int | None:
    """Парсит строку вида '3d', '30m', '2 days', '15 minutes' в секунды. None = без срока указано."""
    if not text or text.strip().lower() in ("perm", "permanent", "навсегда", "-"):
        return None
    match = TIME_RE.match(text.strip())
    if not match:
        raise ValueError("Неверный формат времени. Используйте например: 3d, 30m, 2 days, 15 minutes.")
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


async def notify_punishment(member: discord.Member, punishment: str, reason: str):
    """Уведомляет пользователя в ЛС о полученном наказании. Молча игнорирует закрытые ЛС."""
    embed = discord.Embed(
        title="⚠️ Вы получили наказание",
        description=(
            f"Вы на сервере **{member.guild.name}** получили наказание: **{punishment}**.\n"
            f"Причина: {reason}\n\n"
            f"Если считаете это ошибкой — свяжитесь с руководством сервера."
        ),
        color=discord.Color.red(),
    )
    embed.set_footer(text=member.guild.name)
    try:
        await member.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- MUTE (встроенный Discord timeout) ----------

    @app_commands.command(name="mute", description="Тайм-аут участнику на определённый срок")
    @app_commands.describe(
        username="Кого замьютить",
        time="Срок (например: 3d, 30m). Discord ограничивает максимум 28 днями",
        reason="Причина мьюта",
    )
    @has_mod_permissions()
    async def mute(self, interaction: discord.Interaction, username: discord.Member, time: str, reason: str):
        member = username
        try:
            duration = parse_duration(time)
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        if duration is None:
            duration = MAX_TIMEOUT_SECONDS
        elif duration > MAX_TIMEOUT_SECONDS:
            await interaction.response.send_message(
                "❌ Discord позволяет тайм-аут максимум на 28 дней.", ephemeral=True
            )
            return

        try:
            await member.timeout(
                discord.utils.utcnow() + datetime.timedelta(seconds=duration),
                reason=f"Мьют от {interaction.user}: {reason}",
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ У меня недостаточно прав для тайм-аута.", ephemeral=True)
            return

        duration_text = time if time else "28 дней (максимум Discord)"
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.mute.title"),
            color=discord.Color.orange(),
            description=await t(
                interaction.guild_id, "mod.mute.desc",
                member=member.mention, duration=duration_text, reason=reason,
            ),
        )
        await interaction.response.send_message(embed=embed)
        await notify_punishment(member, f"тайм-аут ({duration_text})", reason)

    @app_commands.command(name="unmute", description="Снять тайм-аут с участника")
    @app_commands.describe(username="С кого снять мьют", reason="Причина")
    @has_mod_permissions()
    async def unmute(self, interaction: discord.Interaction, username: discord.Member, reason: str):
        member = username
        try:
            await member.timeout(None, reason=f"Размьют от {interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ У меня недостаточно прав для снятия тайм-аута.", ephemeral=True)
            return
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unmute.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unmute.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- WARN (тайм-аут на 4 часа) ----------

    @app_commands.command(name="warn", description="Выдать предупреждение участнику (тайм-аут на 4 часа)")
    @app_commands.describe(username="Кому выдать предупреждение", reason="Причина")
    @has_mod_permissions()
    async def warn(self, interaction: discord.Interaction, username: discord.Member, reason: str):
        member = username
        await db.add_warn(interaction.guild_id, member.id, interaction.user.id, reason)
        warns = await db.get_warns(interaction.guild_id, member.id)

        timeout_applied = False
        try:
            await member.timeout(
                discord.utils.utcnow() + datetime.timedelta(seconds=WARN_TIMEOUT_SECONDS),
                reason=f"Предупреждение от {interaction.user}: {reason}",
            )
            timeout_applied = True
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.warn.title"),
            color=discord.Color.yellow(),
            description=await t(
                interaction.guild_id, "mod.warn.desc",
                member=member.mention, reason=reason, count=len(warns),
            ),
        )
        if timeout_applied:
            embed.add_field(name="Наказание", value="⏱️ Тайм-аут на 4 часа", inline=False)
        else:
            embed.add_field(name="Наказание", value="⚠️ Не удалось выдать тайм-аут (недостаточно прав)", inline=False)
        await interaction.response.send_message(embed=embed)
        if timeout_applied:
            await notify_punishment(member, "предупреждение (тайм-аут на 4 часа)", reason)

        # Дополнительное авто-наказание при достижении настроенного лимита предупреждений
        limit = await db.get_warn_limit(interaction.guild_id)
        if limit and len(warns) >= limit:
            try:
                await member.timeout(
                    discord.utils.utcnow() + datetime.timedelta(hours=1),
                    reason=f"Автоматический тайм-аут: достигнут лимит предупреждений ({limit})",
                )
                await interaction.followup.send(
                    f"🚨 {member.mention} достиг лимита предупреждений ({limit}) — "
                    f"тайм-аут продлён до 1 часа."
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "⚠️ Лимит предупреждений достигнут, но у бота недостаточно прав для тайм-аута."
                )

    @app_commands.command(name="warnlimit", description="Настроить порог предупреждений для авто-тайм-аута")
    @app_commands.describe(count="Количество предупреждений (0 — отключить авто-наказание)")
    @app_commands.checks.has_permissions(administrator=True)
    async def warnlimit(self, interaction: discord.Interaction, count: app_commands.Range[int, 0, 50]):
        await db.set_warn_limit(interaction.guild_id, count)
        if count == 0:
            await interaction.response.send_message("✅ Авто-наказание за предупреждения отключено.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"✅ При достижении **{count}** предупреждений участник будет автоматически "
                f"получать тайм-аут на 1 час.",
                ephemeral=True,
            )

    @app_commands.command(name="unwarn", description="Снять последнее предупреждение с участника (и снять тайм-аут)")
    @app_commands.describe(username="С кого снять предупреждение", reason="Причина")
    @has_mod_permissions()
    async def unwarn(self, interaction: discord.Interaction, username: discord.Member, reason: str):
        member = username
        removed = await db.remove_last_warn(interaction.guild_id, member.id)
        if not removed:
            await interaction.response.send_message(
                await t(interaction.guild_id, "mod.unwarn.none"), ephemeral=True
            )
            return

        try:
            if member.is_timed_out():
                await member.timeout(None, reason=f"Предупреждение снято ({interaction.user}): {reason}")
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unwarn.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unwarn.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- BAN ----------

    @app_commands.command(name="ban", description="Забанить участника на определённый срок или навсегда")
    @app_commands.describe(
        username="Кого забанить",
        days="На сколько дней (0 — навсегда)",
        reason="Причина бана",
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, username: discord.Member, days: int, reason: str):
        member = username
        try:
            await member.ban(reason=f"{interaction.user}: {reason}", delete_message_seconds=0)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Недостаточно прав для бана.", ephemeral=True)
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
        await notify_punishment(member, f"бан ({duration_text})", reason)

        if days and days > 0:
            self.bot.loop.create_task(self._scheduled_unban(interaction.guild, member.id, days * 86400))

    async def _scheduled_unban(self, guild: discord.Guild, user_id: int, delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        try:
            await guild.unban(discord.Object(id=user_id), reason="Истёк срок временного бана")
        except (discord.NotFound, discord.Forbidden):
            pass

    @app_commands.command(name="unban", description="Разбанить пользователя по юзернейму или ID")
    @app_commands.describe(username="Юзернейм или ID пользователя", reason="Причина")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, username: str, reason: str):
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
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.unban.title"),
            color=discord.Color.green(),
            description=await t(interaction.guild_id, "mod.unban.desc", user=str(target), reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- KICK ----------

    @app_commands.command(name="kick", description="Кикнуть участника с сервера")
    @app_commands.describe(username="Кого кикнуть", reason="Причина")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, username: discord.Member, reason: str):
        member = username
        try:
            await notify_punishment(member, "кик с сервера", reason)
            await member.kick(reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Недостаточно прав для кика.", ephemeral=True)
            return
        embed = discord.Embed(
            title=await t(interaction.guild_id, "mod.kick.title"),
            color=discord.Color.orange(),
            description=await t(interaction.guild_id, "mod.kick.desc", member=member.mention, reason=reason),
        )
        await interaction.response.send_message(embed=embed)

    # ---------- PROFILE ----------

    @app_commands.command(name="profile", description="Показать профиль участника")
    @app_commands.describe(username="Чей профиль показать (по умолчанию — ваш)")
    async def profile(self, interaction: discord.Interaction, username: discord.Member = None):
        member = username or interaction.user
        embed = discord.Embed(title=f"👤 Профиль {member.display_name}", color=member.color or discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Юзернейм", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(
            name="Аккаунт создан",
            value=discord.utils.format_dt(member.created_at, style="F") + "\n" + discord.utils.format_dt(member.created_at, style="R"),
            inline=False,
        )
        if member.joined_at:
            embed.add_field(
                name="Присоединился к серверу",
                value=discord.utils.format_dt(member.joined_at, style="F") + "\n" + discord.utils.format_dt(member.joined_at, style="R"),
                inline=False,
            )
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        if roles:
            embed.add_field(name=f"Роли ({len(roles)})", value=" ".join(roles[:15]), inline=False)
        await interaction.response.send_message(embed=embed)

    # ---------- SAY / DM ----------

    @app_commands.command(name="say", description="Отправить сообщение от имени бота в указанный канал (embed)")
    @app_commands.describe(channel="Куда отправить", message="Текст сообщения")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        embed = discord.Embed(description=message, color=discord.Color.blurple())
        embed.set_footer(text=f"От имени {interaction.guild.name}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Недостаточно прав отправлять сообщения в этот канал.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Сообщение отправлено в {channel.mention}.", ephemeral=True)

    @app_commands.command(name="dms", description="Отправить личное сообщение от имени бота конкретному участнику")
    @app_commands.describe(username="Кому написать", message="Текст сообщения")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def dms(self, interaction: discord.Interaction, username: discord.Member, message: str):
        member = username
        embed = discord.Embed(description=message, color=discord.Color.blurple())
        embed.set_footer(text=f"Сообщение от администрации {interaction.guild.name}")
        try:
            await member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                f"⚠️ Не удалось отправить сообщение {member.mention} — вероятно, у него закрыты ЛС.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(f"✅ Сообщение отправлено {member.mention} в ЛС.", ephemeral=True)

    @app_commands.command(name="dmall", description="Отправить сообщение в ЛС всем участникам сервера")
    @app_commands.describe(message="Текст сообщения")
    @app_commands.checks.has_permissions(administrator=True)
    async def dmall(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(
            f"⏳ Начинаю рассылку {interaction.guild.member_count} участникам, это может занять время...",
            ephemeral=True,
        )
        embed = discord.Embed(description=message, color=discord.Color.blurple())
        embed.set_footer(text=f"Сообщение от администрации {interaction.guild.name}")

        sent, failed = 0, 0
        for member in interaction.guild.members:
            if member.bot:
                continue
            try:
                await member.send(embed=embed)
                sent += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
            await asyncio.sleep(1)  # избегаем рейт-лимитов Discord на личные сообщения

        await interaction.followup.send(
            f"✅ Рассылка завершена. Доставлено: **{sent}**, не удалось доставить: **{failed}**.",
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                await t(interaction.guild_id, "mod.noperm"), ephemeral=True
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
