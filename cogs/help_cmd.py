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
            "`/mute [member] [time] [reason]`\n"
            "`/unmute [member] [reason]`\n"
            "`/warn [member] [reason]`\n"
            "`/warnlimit [count]`\n"
            "`/unwarn [member] [reason]`\n"
            "`/ban [member] [days] [reason]`\n"
            "`/unban [username] [reason]`\n"
            "`/kick [member] [reason]`"
        ),
        inline=False,
    )
    embed.add_field(
        name=await t(gid, "help.general"),
        value="`/report`\n`/support`\n`/help`\n`/language`",
        inline=False,
    )
    embed.add_field(
        name=await t(gid, "help.admin"),
        value=(
            "`/autorole setup|channel|role|message|enable|disable|status`\n"
            "`/reportsettings channel`\n"
            "`/logsettings channel`\n"
            "`/antispam on|off|allow`\n"
            "`/language`"
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
