import discord
from discord import app_commands
from discord.ext import commands

import database as db
from i18n import t, get_lang, VIOLATION_CATEGORIES


class ReportModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, category_label: str):
        self.category_label = category_label
        self.bot = bot
        super().__init__(title="📢 Report")
        self.target_username = discord.ui.TextInput(
            label="Юзернейм нарушителя / Target username", required=True
        )
        self.violation = discord.ui.TextInput(
            label="Опишите нарушение / Describe the violation",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.target_username)
        self.add_item(self.violation)

    async def on_submit(self, interaction: discord.Interaction):
        gid = interaction.guild_id
        embed = discord.Embed(title=await t(gid, "report.new_title"), color=discord.Color.red())
        embed.add_field(name=await t(gid, "report.reporter"), value=interaction.user.mention, inline=False)
        embed.add_field(name=await t(gid, "report.target"), value=self.target_username.value, inline=False)
        embed.add_field(name=await t(gid, "report.category"), value=self.category_label, inline=False)
        embed.add_field(name=await t(gid, "report.violation"), value=self.violation.value, inline=False)
        embed.add_field(name="Статус", value="🟡 На рассмотрении", inline=False)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        report_channel_id = await db.get_report_channel(gid)
        report_channel = interaction.guild.get_channel(report_channel_id) if report_channel_id else None
        target_channel = report_channel or interaction.channel

        try:
            await target_channel.send(
                embed=embed,
                view=ReportReviewView(self.target_username.value),
            )
        except discord.Forbidden:
            pass

        view = EvidenceChoiceView(self.bot, target_channel, interaction.user.id)
        await interaction.response.send_message(
            content=(await t(gid, "report.accepted")) + "\n" + (await t(gid, "report.evidence.prompt")),
            view=view,
            ephemeral=True,
        )


class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, lang: str):
        options = [
            discord.SelectOption(label=label, value=key)
            for key, label in VIOLATION_CATEGORIES.get(lang, VIOLATION_CATEGORIES["ru"])
        ]
        super().__init__(placeholder="Категория / Category", options=options, min_values=1, max_values=1)
        self.bot = bot
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        label = self.options[[o.value for o in self.options].index(self.values[0])].label
        await interaction.response.send_modal(ReportModal(self.bot, label))


class CategoryView(discord.ui.View):
    def __init__(self, bot: commands.Bot, lang: str):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(bot, lang))


class EvidenceChoiceView(discord.ui.View):
    def __init__(self, bot: commands.Bot, target_channel: discord.abc.Messageable, author_id: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.target_channel = target_channel
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Прикрепить фото / Attach photos", style=discord.ButtonStyle.primary, emoji="📎")
    async def attach(self, interaction: discord.Interaction, button: discord.ui.Button):
        gid = interaction.guild_id
        await interaction.response.edit_message(content=await t(gid, "report.evidence.waiting"), view=None)

        def check(m: discord.Message):
            return m.author.id == self.author_id and m.channel.id == interaction.channel.id

        try:
            evidence_msg = await self.bot.wait_for("message", check=check, timeout=120)
        except Exception:
            await interaction.followup.send(await t(gid, "report.evidence.timeout"), ephemeral=True)
            return

        attachments = evidence_msg.attachments[:10]
        if attachments:
            files = [await a.to_file() for a in attachments]
            try:
                await self.target_channel.send(
                    content=await t(gid, "report.evidence.received", count=len(files)), files=files
                )
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Без доказательств / Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅", view=None)


def has_review_permissions(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return perms.moderate_members or perms.kick_members or perms.ban_members or perms.administrator


class PunishmentModal(discord.ui.Modal, title="⚖️ Применить наказание"):
    reason = discord.ui.TextInput(
        label="Причина", style=discord.TextStyle.paragraph, required=True, max_length=500
    )
    duration = discord.ui.TextInput(
        label="Срок (для мьюта/бана, например 1d, 30m). Пусто = навсегда/1ч",
        required=False,
        max_length=20,
    )

    def __init__(self, target_username: str, punishment: str, original_message: discord.Message, original_embed: discord.Embed):
        super().__init__()
        self.target_username = target_username
        self.punishment = punishment
        self.original_message = original_message
        self.original_embed = original_embed

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = discord.utils.find(
            lambda m: m.name.lower() == self.target_username.lower()
            or str(m) == self.target_username
            or (self.target_username.isdigit() and m.id == int(self.target_username)),
            guild.members,
        )

        if member is None:
            await interaction.response.send_message(
                f"⚠️ Не удалось найти участника `{self.target_username}` на сервере. "
                f"Наказание не применено, но жалоба будет помечена как одобренная.",
                ephemeral=True,
            )
            applied_note = "⚠️ Участник не найден — наказание не применено вручную."
        else:
            applied_note = await self._apply_punishment(member, interaction)

        embed = self.original_embed.copy()
        for i, field in enumerate(embed.fields):
            if field.name == "Статус":
                embed.set_field_at(i, name="Статус", value=f"✅ Одобрено ({self.punishment})", inline=False)
                break
        embed.add_field(name="Обработал", value=interaction.user.mention, inline=False)
        embed.add_field(name="Причина наказания", value=self.reason.value, inline=False)
        embed.add_field(name="Результат", value=applied_note, inline=False)
        embed.color = discord.Color.green()

        await self.original_message.edit(embed=embed, view=None)
        if not interaction.response.is_done():
            await interaction.response.send_message("✅ Жалоба одобрена, наказание обработано.", ephemeral=True)

    async def _apply_punishment(self, member: discord.Member, interaction: discord.Interaction) -> str:
        import re as _re
        import datetime as _dt

        reason_text = f"По жалобе, одобрено {interaction.user}: {self.reason.value}"
        try:
            if self.punishment == "warn":
                await db.add_warn(interaction.guild_id, member.id, interaction.user.id, self.reason.value)
                return f"⚠️ Выдано предупреждение {member.mention}."

            if self.punishment == "timeout":
                minutes = 60
                if self.duration.value:
                    match = _re.match(r"^(\d+)\s*(d|m)$", self.duration.value.strip().lower())
                    if match:
                        amount, unit = int(match.group(1)), match.group(2)
                        minutes = amount * 1440 if unit == "d" else amount
                await member.timeout(_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(minutes=minutes), reason=reason_text)
                return f"⏱️ Тайм-аут на {minutes} мин. выдан {member.mention}."

            if self.punishment == "kick":
                await member.kick(reason=reason_text)
                return f"👢 {member.mention} кикнут."

            if self.punishment == "ban":
                await member.ban(reason=reason_text, delete_message_seconds=0)
                return f"🔨 {member.mention} забанен."
        except discord.Forbidden:
            return "❌ Недостаточно прав для применения наказания."

        return "—"


class PunishmentSelect(discord.ui.Select):
    def __init__(self, target_username: str, original_message: discord.Message, original_embed: discord.Embed):
        options = [
            discord.SelectOption(label="Предупреждение (warn)", value="warn", emoji="⚠️"),
            discord.SelectOption(label="Тайм-аут (timeout)", value="timeout", emoji="⏱️"),
            discord.SelectOption(label="Кик (kick)", value="kick", emoji="👢"),
            discord.SelectOption(label="Бан (ban)", value="ban", emoji="🔨"),
        ]
        super().__init__(placeholder="Выберите наказание", options=options, min_values=1, max_values=1)
        self.target_username = target_username
        self.original_message = original_message
        self.original_embed = original_embed

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            PunishmentModal(self.target_username, self.values[0], self.original_message, self.original_embed)
        )


class PunishmentSelectView(discord.ui.View):
    def __init__(self, target_username: str, original_message: discord.Message, original_embed: discord.Embed):
        super().__init__(timeout=120)
        self.add_item(PunishmentSelect(target_username, original_message, original_embed))


class ReportReviewView(discord.ui.View):
    """Кнопки Одобрить/Отклонить под жалобой. Видны всем, но нажать может только модератор."""

    def __init__(self, target_username: str):
        super().__init__(timeout=None)  # кнопки должны жить долго, пока жалоба не обработана
        self.target_username = target_username

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.success, emoji="✅", custom_id="report_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_review_permissions(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав модерации для этого действия.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        target_username = self.target_username
        if not target_username:
            for field in embed.fields:
                if "На кого" in field.name or "Reported" in field.name:
                    target_username = field.value
                    break
        await interaction.response.send_message(
            "Выберите наказание для нарушителя:",
            view=PunishmentSelectView(target_username, interaction.message, embed),
            ephemeral=True,
        )

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, emoji="❌", custom_id="report_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_review_permissions(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав модерации для этого действия.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "Статус":
                embed.set_field_at(i, name="Статус", value="❌ Отклонено", inline=False)
                break
        embed.add_field(name="Обработал", value=interaction.user.mention, inline=False)
        embed.color = discord.Color.dark_grey()
        await interaction.response.edit_message(embed=embed, view=None)


@app_commands.command(name="report", description="Пожаловаться на нарушителя / Report a rule violation")
async def report(interaction: discord.Interaction):
    lang = await get_lang(interaction.guild_id)
    await interaction.response.send_message(
        await t(interaction.guild_id, "report.select.placeholder"),
        view=CategoryView(interaction.client, lang),
        ephemeral=True,
    )


report_settings_group = app_commands.Group(
    name="reportsettings", description="Настройки системы жалоб (для администрации)"
)


@report_settings_group.command(name="channel", description="Указать канал, куда будут приходить жалобы")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="Канал для жалоб")
async def report_channel_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.set_report_channel(interaction.guild_id, channel.id)
    await interaction.response.send_message(f"✅ Канал жалоб установлен: {channel.mention}", ephemeral=True)


class Report(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Регистрируем persistent view, чтобы кнопки Одобрить/Отклонить работали
        # и после перезапуска бота (custom_id делает view "долгоживущим")
        self.bot.add_view(ReportReviewView(target_username=""))


async def setup(bot: commands.Bot):
    bot.tree.add_command(report)
    bot.tree.add_command(report_settings_group)
    await bot.add_cog(Report(bot))
