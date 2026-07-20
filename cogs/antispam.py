import re

import discord
from discord import app_commands
from discord.ext import commands

import database as db

URL_RE = re.compile(r"(https?://|www\.)[^\s]+", re.IGNORECASE)

# Домены, которые считаются безопасными по умолчанию (можно расширять через /links allow)
DEFAULT_SAFE_DOMAINS = {
    "tenor.com",
    "giphy.com",
    "youtube.com",
    "youtu.be",
    "cdn.discordapp.com",
    "media.discordapp.net",
}


def extract_domain(url: str) -> str:
    url = url.lower().replace("http://", "").replace("https://", "").replace("www.", "")
    return url.split("/")[0]


antispam_group = app_commands.Group(name="antispam", description="Управление антиспам-фильтром ссылок")


@antispam_group.command(name="on", description="Включить автоудаление спам-ссылок")
@app_commands.checks.has_permissions(administrator=True)
async def antispam_on(interaction: discord.Interaction):
    await db.set_antispam_enabled(interaction.guild_id, True)
    await interaction.response.send_message("✅ Антиспам-фильтр ссылок включён.", ephemeral=True)


@antispam_group.command(name="off", description="Выключить автоудаление спам-ссылок")
@app_commands.checks.has_permissions(administrator=True)
async def antispam_off(interaction: discord.Interaction):
    await db.set_antispam_enabled(interaction.guild_id, False)
    await interaction.response.send_message("✅ Антиспам-фильтр ссылок выключен.", ephemeral=True)


@antispam_group.command(name="allow", description="Добавить домен в список разрешённых ссылок")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(domain="Домен, например: example.com")
async def antispam_allow(interaction: discord.Interaction, domain: str):
    await db.add_allowed_domain(interaction.guild_id, domain)
    await interaction.response.send_message(f"✅ Домен `{domain}` добавлен в разрешённые.", ephemeral=True)


class AntiSpam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Модераторы и администраторы не фильтруются
        if isinstance(message.author, discord.Member) and message.author.guild_permissions.manage_messages:
            return

        if not await db.get_antispam_enabled(message.guild.id):
            return

        if not URL_RE.search(message.content):
            return

        allowed = DEFAULT_SAFE_DOMAINS | await db.get_allowed_domains(message.guild.id)

        full_matches = [m.group(0) for m in URL_RE.finditer(message.content)]
        is_spam = False
        for url in full_matches:
            domain = extract_domain(url)
            if not any(domain == d or domain.endswith("." + d) for d in allowed):
                is_spam = True
                break

        if is_spam:
            try:
                await message.delete()
            except discord.Forbidden:
                return
            try:
                warn_msg = await message.channel.send(
                    f"🚫 {message.author.mention}, ссылки на посторонние ресурсы запрещены на этом сервере.",
                    delete_after=8,
                )
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    bot.tree.add_command(antispam_group)
    await bot.add_cog(AntiSpam(bot))
