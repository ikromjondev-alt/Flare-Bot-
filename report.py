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
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        report_channel_id = await db.get_report_channel(gid)
        report_channel = interaction.guild.get_channel(report_channel_id) if report_channel_id else None
        target_channel = report_channel or interaction.channel

        try:
            await target_channel.send(embed=embed)
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


async def setup(bot: commands.Bot):
    bot.tree.add_command(report)
    bot.tree.add_command(report_settings_group)
    await bot.add_cog(Report(bot))
