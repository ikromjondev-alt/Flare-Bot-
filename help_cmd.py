import discord
from discord import app_commands
from discord.ext import commands

from i18n import t


@app_commands.command(name="help", description="Показать список всех команд бота / Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    gid = interaction.guild_id
    embed = discord.Embed(title=await t(gid, "help.title"), color=discord.Color.blurple())
    embed.add_field(
        name=await t(gid, "help.moderation"),
        value=(
            "`/mute [username] [time] [reason]` — тайм-аут\n"
            "`/unmute [username] [reason]`\n"
            "`/warn [username] [reason]` — тайм-аут на 4 часа\n"
            "`/unwarn [username] [reason]`\n"
            "`/warnlimit [count]`\n"
            "`/ban [username] [days] [reason]`\n"
            "`/unban [username] [reason]`\n"
            "`/kick [username] [reason]`"
        ),
        inline=False,
    )
    embed.add_field(
        name=await t(gid, "help.general"),
        value=(
            "`/profile [@username]` — профиль участника\n"
            "`/support` — связаться с владельцем\n"
            "`/help` — это меню\n"
            "`/language` — сменить язык"
        ),
        inline=False,
    )
    embed.add_field(
        name=await t(gid, "help.admin"),
        value=(
            "`/autorole [channel] [role] [message]` — авто-роль (включается сразу)\n"
            "`/autorole_off` — выключить авто-роль\n"
            "`!setreport` — отправить панель подачи жалоб (не слэш-команда)\n"
            "`/verdict [thread] [решение]` — вердикт по жалобе (внутри треда жалобы)\n"
            "`/reportsettings channel` — канал уведомлений о жалобах\n"
            "`/logsettings channel` — канал логов\n"
            "`/antispam on|off|allow`\n"
            "`/say [channel] [message]` — сообщение от бота (embed)\n"
            "`/dms [username] [message]` — личное сообщение от бота\n"
            "`/dmall [message]` — сообщение всем участникам сервера в ЛС"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.tree.add_command(help_cmd)
    await bot.add_cog(HelpCog(bot))
