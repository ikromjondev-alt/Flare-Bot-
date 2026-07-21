import discord
from discord import app_commands
from discord.ext import commands

import config


def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return config.OWNER_ID and str(interaction.user.id) == str(config.OWNER_ID)
    return app_commands.check(predicate)


@app_commands.command(name="webapp", description="Инструкция по запуску веб-панели управления (только для владельца)")
@is_owner()
async def webapp_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🖥️ Веб-панель управления",
        description="Панель — отдельный процесс, её нужно запускать отдельно от бота.",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="1️⃣ На хостинге (Wispbyte)",
        value=(
            "Создайте отдельный сервер/приложение на хостинге с тем же кодом, "
            "укажите главный файл `webpanel/app.py` вместо `bot.py`. "
            "Если хостинг поддерживает веб-сервисы (Web Service / HTTP порт), "
            "он выдаст вам публичный адрес — панель будет доступна по нему."
        ),
        inline=False,
    )
    embed.add_field(
        name="2️⃣ Локально на компьютере",
        value="```\ncd webpanel\npython app.py\n```\nОткрыть в браузере: `http://localhost:5000`",
        inline=False,
    )
    embed.add_field(
        name="3️⃣ Вход в панель",
        value="Пароль указан в `.env` в переменной `WEBPANEL_PASSWORD`.",
        inline=False,
    )
    embed.add_field(
        name="⚠️ Важно",
        value=(
            "Панель и бот должны использовать один и тот же файл базы данных "
            "(`bot_database.db`), иначе изменения в панели бот не увидит."
        ),
        inline=False,
    )
    embed.set_footer(text="Эта команда видна только владельцу бота.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@webapp_cmd.error
async def webapp_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ Эта команда недоступна.", ephemeral=True)
    else:
        raise error


class WebApp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(webapp_cmd)
    await bot.add_cog(WebApp(bot))
