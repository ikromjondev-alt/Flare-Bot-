import discord
from discord import app_commands
from discord.ext import commands

import database as db
from i18n import get_lang, VIOLATION_CATEGORIES


def has_review_permissions(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return perms.moderate_members or perms.kick_members or perms.ban_members or perms.administrator


async def get_or_create_report_forum(guild: discord.Guild) -> discord.ForumChannel | None:
    """Возвращает форум-канал для жалоб, создавая его при первой необходимости."""
    forum_id = await db.get_report_forum(guild.id)
    forum = guild.get_channel(forum_id) if forum_id else None
    if isinstance(forum, discord.ForumChannel):
        return forum

    # Пытаемся найти уже существующий форум с подходящим именем
    forum = discord.utils.get(guild.forums, name="жалобы")
    if forum is None:
        try:
            forum = await guild.create_forum(
                name="жалобы",
                reason="Автоматическое создание форума для системы жалоб",
                topic="Здесь появляются все жалобы, поданные через панель.",
            )
        except discord.Forbidden:
            return None
    await db.set_report_forum(guild.id, forum.id)
    return forum


# ---------- Модалка: юзернейм нарушителя + описание ----------

class ReportDetailsModal(discord.ui.Modal, title="📢 Подать жалобу"):
    target_username = discord.ui.TextInput(
        label="Юзернейм нарушителя", placeholder="например: someuser", required=True
    )
    description = discord.ui.TextInput(
        label="Опишите нарушение",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    def __init__(self, bot: commands.Bot, category_label: str):
        super().__init__()
        self.bot = bot
        self.category_label = category_label

    async def on_submit(self, interaction: discord.Interaction):
        # Просим прислать доказательства в ЛС — там же будет создан тикет-жалоба
        await interaction.response.send_message(
            "✅ Жалоба принята. Проверьте личные сообщения от бота — там нужно прислать "
            "доказательства (скриншот/видео), после чего жалоба будет отправлена на рассмотрение.",
            ephemeral=True,
        )
        try:
            dm = await interaction.user.create_dm()
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ Не удалось написать вам в ЛС — откройте личные сообщения от участников сервера и "
                "попробуйте снова.",
                ephemeral=True,
            )
            return

        await dm.send(
            f"📎 Пришлите сюда скриншот(ы) или видео-доказательства по вашей жалобе на "
            f"**{self.target_username.value}** (категория: {self.category_label}).\n"
            f"У вас есть 5 минут. Можно приложить несколько файлов в одном сообщении."
        )

        def check(m: discord.Message):
            return m.author.id == interaction.user.id and m.channel.id == dm.id

        try:
            evidence_msg = await self.bot.wait_for("message", check=check, timeout=300)
        except Exception:
            await dm.send("⏱️ Время ожидания доказательств истекло. Жалоба отправлена без вложений.")
            evidence_msg = None

        attachments = evidence_msg.attachments[:10] if evidence_msg else []
        await self._create_ticket(interaction, attachments)

    async def _create_ticket(self, interaction: discord.Interaction, attachments: list[discord.Attachment]):
        guild = interaction.guild
        forum = await get_or_create_report_forum(guild)

        embed = discord.Embed(title="📢 Новая жалоба", color=discord.Color.red())
        embed.add_field(name="Жалобщик", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="Нарушитель", value=self.target_username.value, inline=False)
        embed.add_field(name="Категория", value=self.category_label, inline=False)
        embed.add_field(name="Описание", value=self.description.value, inline=False)
        embed.add_field(
            name="Доказательства",
            value=f"📎 {len(attachments)} файл(ов)" if attachments else "Не приложены",
            inline=False,
        )
        embed.add_field(name="Вердикт администрации", value="🟡 На рассмотрении", inline=False)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        files = [await a.to_file() for a in attachments] if attachments else []

        if forum is None:
            # Форум создать не удалось (нет прав) — шлём в обычный канал жалоб как запасной вариант
            fallback_channel_id = await db.get_report_channel(guild.id)
            fallback = guild.get_channel(fallback_channel_id) if fallback_channel_id else None
            if fallback:
                await fallback.send(embed=embed, files=files)
            try:
                dm = await interaction.user.create_dm()
                await dm.send("✅ Жалоба отправлена на рассмотрение.")
            except discord.Forbidden:
                pass
            return

        thread_name = f"Жалоба на {self.target_username.value}"[:100]
        thread_with_message = await forum.create_thread(name=thread_name, embed=embed, files=files)

        try:
            dm = await interaction.user.create_dm()
            await dm.send(f"✅ Жалоба отправлена на рассмотрение: {thread_with_message.thread.jump_url}")
        except discord.Forbidden:
            pass


# ---------- Панель категорий (постоянная, отправляется командой !setreport) ----------

class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        options = [
            discord.SelectOption(label=label, value=key)
            for key, label in VIOLATION_CATEGORIES.get("ru", [])
        ]
        super().__init__(
            placeholder="Выберите категорию нарушения",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="report_category_select",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        label = self.options[[o.value for o in self.options].index(self.values[0])].label
        await interaction.response.send_modal(ReportDetailsModal(self.bot, label))


class ReportPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)  # постоянная панель, должна жить вечно
        self.add_item(CategorySelect(bot))


# ---------- Вердикт по жалобе ----------

@app_commands.command(name="verdict", description="Вынести вердикт по жалобе (вызывать внутри треда жалобы)")
@app_commands.describe(decision="Решение и комментарий администрации по жалобе")
@app_commands.checks.has_permissions(moderate_members=True)
async def verdict_cmd(interaction: discord.Interaction, decision: str):
    channel = interaction.channel
    if not isinstance(channel, discord.Thread):
        await interaction.response.send_message(
            "❌ Эту команду нужно использовать внутри треда конкретной жалобы.", ephemeral=True
        )
        return

    # Ищем исходное сообщение с embed жалобы — это стартовое сообщение треда
    try:
        starter = await channel.parent.fetch_message(channel.id)
    except (discord.NotFound, discord.Forbidden, AttributeError):
        starter = None

    if starter is None or not starter.embeds:
        await interaction.response.send_message("❌ Не удалось найти исходное сообщение жалобы.", ephemeral=True)
        return

    embed = starter.embeds[0]
    for i, field in enumerate(embed.fields):
        if field.name == "Вердикт администрации":
            embed.set_field_at(
                i, name="Вердикт администрации",
                value=f"{decision}\n— {interaction.user.mention}", inline=False,
            )
            break
    embed.color = discord.Color.green()

    await starter.edit(embed=embed)
    await interaction.response.send_message("✅ Вердикт добавлен к жалобе.", ephemeral=True)


# ---------- Настройки ----------

report_settings_group = app_commands.Group(
    name="reportsettings", description="Настройки системы жалоб (для администрации)"
)


@report_settings_group.command(name="channel", description="Запасной канал жалоб (если форум создать не удалось)")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Канал для жалоб")
async def report_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_report_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Запасной канал жалоб установлен: {channel.mention}", ephemeral=True)


class Report(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Регистрируем постоянную панель, чтобы выпадающее меню категорий работало
        # и после перезапуска бота
        self.bot.add_view(ReportPanelView(bot))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.strip().lower() != "!setreport":
            return
        if not message.author.guild_permissions.administrator:
            return

        embed = discord.Embed(
            title="📢 Подать жалобу",
            description=(
                "Выберите категорию нарушения из списка ниже, чтобы подать жалобу.\n\n"
                "После выбора откроется форма с описанием, а доказательства нужно будет "
                "прислать боту в личные сообщения."
            ),
            color=discord.Color.blurple(),
        )
        try:
            await message.channel.send(embed=embed, view=ReportPanelView(self.bot))
            await message.delete()
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    bot.tree.add_command(verdict_cmd)
    bot.tree.add_command(report_settings_group)
    await bot.add_cog(Report(bot))
