import discord
from discord.ext import commands

import database as db
from i18n import t


class Welcome(commands.Cog):
    """Отправляет приветственное сообщение новому участнику (стиль как у Flare Bot)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg = await db.get_autorole_config(guild.id)
        channel = None
        role = None
        custom_message = None

        if cfg:
            channel_id, role_id, custom_message, enabled = cfg
            if channel_id:
                channel = guild.get_channel(channel_id)
            if enabled and role_id:
                role = guild.get_role(role_id)

        if channel is None:
            channel = guild.system_channel
        if channel is None:
            return  # нет канала для приветствия — ничего не отправляем

        member_count = guild.member_count

        embed = discord.Embed(
            title=await t(guild.id, "welcome.title"),
            description=await t(guild.id, "welcome.desc", mention=member.mention),
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name=await t(guild.id, "welcome.member_field"), value=member.mention, inline=True)
        embed.add_field(
            name=await t(guild.id, "welcome.count_field"),
            value=await t(guild.id, "welcome.count_value", count=member_count),
            inline=True,
        )
        if custom_message:
            embed.add_field(name=await t(guild.id, "welcome.admin_msg_field"), value=custom_message, inline=False)
        embed.set_footer(text=await t(guild.id, "welcome.footer", guild=guild.name))
        embed.timestamp = discord.utils.utcnow()

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

        # Авто-выдача роли, если она настроена и включена
        if role:
            try:
                await member.add_roles(role, reason="Авто-выдача роли при входе")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
