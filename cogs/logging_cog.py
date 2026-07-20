import discord
from discord import app_commands
from discord.ext import commands

import database as db

log_settings_group = app_commands.Group(name="logsettings", description="Настройка канала логов")


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

    # ---------- Вступление / выход из сервера ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            description=f"📥 {member.mention} присоединился к серверу.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        await self._log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            description=f"📤 {member.mention} покинул сервер.",
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        await self._log(member.guild, embed)

    # ---------- Сообщения ----------

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = discord.Embed(
            description=f"🗑️ Сообщение от {message.author.mention} удалено в {message.channel.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        if message.content:
            embed.add_field(name="Содержимое", value=message.content[:1000], inline=False)
        await self._log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = discord.Embed(
            description=f"✏️ Сообщение от {before.author.mention} отредактировано в {before.channel.mention}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="До", value=(before.content or "—")[:500], inline=False)
        embed.add_field(name="После", value=(after.content or "—")[:500], inline=False)
        await self._log(before.guild, embed)

    # ---------- Голосовые каналы ----------

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild

        # Вход/выход из войса
        if before.channel != after.channel:
            if after.channel and not before.channel:
                embed = discord.Embed(
                    description=f"🔊 {member.mention} зашёл в голосовой канал **{after.channel.name}**",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                await self._log(guild, embed)
            elif before.channel and not after.channel:
                embed = discord.Embed(
                    description=f"🔇 {member.mention} вышел из голосового канала **{before.channel.name}**",
                    color=discord.Color.dark_grey(),
                    timestamp=discord.utils.utcnow(),
                )
                await self._log(guild, embed)
            elif before.channel and after.channel:
                embed = discord.Embed(
                    description=(
                        f"🔀 {member.mention} перешёл из **{before.channel.name}** "
                        f"в **{after.channel.name}**"
                    ),
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow(),
                )
                await self._log(guild, embed)

        # Кто кому включил/выключил звук (серверный мьют/деафен)
        if before.mute != after.mute:
            state = "выключил" if after.mute else "включил"
            embed = discord.Embed(
                description=f"🎙️ Серверный микрофон участника {member.mention} был **{state}** модератором.",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            await self._log(guild, embed)

        if before.deaf != after.deaf:
            state = "выключил" if after.deaf else "включил"
            embed = discord.Embed(
                description=f"🎧 Серверный звук у {member.mention} был **{state}** модератором.",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            await self._log(guild, embed)

    # ---------- Роли ----------

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = discord.Embed(
            description=f"➕ Создана роль **{role.name}**",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = discord.Embed(
            description=f"➖ Удалена роль **{role.name}**",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        await self._log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        changes = []
        if before.name != after.name:
            changes.append(f"название: **{before.name}** → **{after.name}**")
        if before.permissions != after.permissions:
            changes.append("изменены права роли")
        if before.color != after.color:
            changes.append("изменён цвет роли")
        if not changes:
            return
        embed = discord.Embed(
            description=f"✏️ Роль **{after.name}** изменена: " + "; ".join(changes),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        await self._log(after.guild, embed)


async def setup(bot: commands.Bot):
    bot.tree.add_command(log_settings_group)
    await bot.add_cog(LoggingCog(bot))
