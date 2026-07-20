"""
Internationalization module.
Language stored per-guild in guild_settings table.
Usage: from i18n import t
       text = await t(guild_id, "welcome.title")
"""

import database as db

STRINGS = {
    "ru": {
        "welcome.title": "👋 Добро пожаловать!",
        "welcome.desc": "Рады видеть тебя, {mention}!\n\n📜 Ознакомься с правилами сервера и чувствуй себя как дома.\n💬 Не стесняйся общаться — мы рады каждому новому участнику!",
        "welcome.member_field": "👤 Участник",
        "welcome.count_field": "🎉 Ты стал",
        "welcome.count_value": "**{count}**-м участником!",
        "welcome.admin_msg_field": "📝 Сообщение от администрации",
        "welcome.footer": "{guild} • Добро пожаловать в семью!",

        "support.title": "🛠️ Поддержка",
        "support.desc": "Приветствую. Для обращения в поддержку пишите в личные сообщения **{username}**.\n(Точка есть на моём юзернейме)",

        "help.title": "📖 Команды бота",
        "help.moderation": "Модерация",
        "help.general": "Общее",
        "help.admin": "Администрирование",

        "mod.mute.title": "🔇 Участник замьючен",
        "mod.mute.desc": "**Участник:** {member}\n**Срок:** {duration}\n**Причина:** {reason}",
        "mod.mute.forever": "навсегда",
        "mod.unmute.title": "🔊 Мьют снят",
        "mod.unmute.desc": "**Участник:** {member}\n**Причина:** {reason}",
        "mod.warn.title": "⚠️ Предупреждение выдано",
        "mod.warn.desc": "**Участник:** {member}\n**Причина:** {reason}\n**Всего предупреждений:** {count}",
        "mod.unwarn.title": "✅ Предупреждение снято",
        "mod.unwarn.desc": "**Участник:** {member}\n**Причина:** {reason}",
        "mod.unwarn.none": "У этого участника нет предупреждений.",
        "mod.ban.title": "🔨 Участник забанен",
        "mod.ban.desc": "**Участник:** {member}\n**Срок:** {duration}\n**Причина:** {reason}",
        "mod.ban.days": "{days} дн.",
        "mod.unban.title": "✅ Пользователь разбанен",
        "mod.unban.desc": "**Пользователь:** {user}\n**Причина:** {reason}",
        "mod.unban.notfound": "Пользователь не найден в списке забаненных.",
        "mod.kick.title": "👢 Участник кикнут",
        "mod.kick.desc": "**Участник:** {member}\n**Причина:** {reason}",
        "mod.noperm": "❌ У вас нет прав для использования этой команды.",

        "report.modal.title": "📢 Подать жалобу",
        "report.select.placeholder": "Выберите категорию нарушения",
        "report.accepted": "✅ Жалоба принята! Спасибо, что помогаете следить за порядком.",
        "report.evidence.prompt": "📎 Хотите прикрепить доказательства (до 10 фото)?",
        "report.evidence.btn_add": "Прикрепить фото",
        "report.evidence.btn_skip": "Без доказательств",
        "report.evidence.waiting": "Пришлите до 10 фото одним сообщением в этом канале (2 минуты).",
        "report.evidence.received": "📎 Доказательства к жалобе выше ({count} шт.):",
        "report.evidence.timeout": "⏱️ Время ожидания доказательств истекло.",
        "report.new_title": "📢 Новая жалоба",
        "report.reporter": "Отправитель",
        "report.target": "На кого жалоба",
        "report.category": "Категория",
        "report.violation": "Нарушение",

        "lang.set": "✅ Язык бота на этом сервере изменён на: {lang}",
    },
    "en": {
        "welcome.title": "👋 Welcome!",
        "welcome.desc": "Great to have you here, {mention}!\n\n📜 Please check out the server rules and make yourself at home.\n💬 Feel free to chat — we\'re glad to have every new member!",
        "welcome.member_field": "👤 Member",
        "welcome.count_field": "🎉 You are",
        "welcome.count_value": "member **#{count}**!",
        "welcome.admin_msg_field": "📝 Message from staff",
        "welcome.footer": "{guild} • Welcome to the family!",

        "support.title": "🛠️ Support",
        "support.desc": "Hello! For support, please DM **{username}**.",

        "help.title": "📖 Bot Commands",
        "help.moderation": "Moderation",
        "help.general": "General",
        "help.admin": "Administration",

        "mod.mute.title": "🔇 Member muted",
        "mod.mute.desc": "**Member:** {member}\n**Duration:** {duration}\n**Reason:** {reason}",
        "mod.mute.forever": "permanent",
        "mod.unmute.title": "🔊 Mute removed",
        "mod.unmute.desc": "**Member:** {member}\n**Reason:** {reason}",
        "mod.warn.title": "⚠️ Warning issued",
        "mod.warn.desc": "**Member:** {member}\n**Reason:** {reason}\n**Total warnings:** {count}",
        "mod.unwarn.title": "✅ Warning removed",
        "mod.unwarn.desc": "**Member:** {member}\n**Reason:** {reason}",
        "mod.unwarn.none": "This member has no warnings.",
        "mod.ban.title": "🔨 Member banned",
        "mod.ban.desc": "**Member:** {member}\n**Duration:** {duration}\n**Reason:** {reason}",
        "mod.ban.days": "{days} day(s)",
        "mod.unban.title": "✅ User unbanned",
        "mod.unban.desc": "**User:** {user}\n**Reason:** {reason}",
        "mod.unban.notfound": "User not found in the ban list.",
        "mod.kick.title": "👢 Member kicked",
        "mod.kick.desc": "**Member:** {member}\n**Reason:** {reason}",
        "mod.noperm": "❌ You don\'t have permission to use this command.",

        "report.modal.title": "📢 Submit a report",
        "report.select.placeholder": "Select a violation category",
        "report.accepted": "✅ Report received! Thanks for helping keep the server safe.",
        "report.evidence.prompt": "📎 Would you like to attach evidence (up to 10 photos)?",
        "report.evidence.btn_add": "Attach photos",
        "report.evidence.btn_skip": "No evidence",
        "report.evidence.waiting": "Send up to 10 photos in one message in this channel (2 minutes).",
        "report.evidence.received": "📎 Evidence for the report above ({count} file(s)):",
        "report.evidence.timeout": "⏱️ Timed out waiting for evidence.",
        "report.new_title": "📢 New Report",
        "report.reporter": "Reporter",
        "report.target": "Reported user",
        "report.category": "Category",
        "report.violation": "Violation details",

        "lang.set": "✅ Bot language for this server set to: {lang}",
    },
}

VIOLATION_CATEGORIES = {
    "ru": [
        ("spam", "🔁 Спам"),
        ("insult", "🤬 Оскорбления"),
        ("advert", "📢 Реклама"),
        ("cheat", "⚙️ Читерство"),
        ("nsfw", "🔞 Неприемлемый контент"),
        ("other", "❓ Другое"),
    ],
    "en": [
        ("spam", "🔁 Spam"),
        ("insult", "🤬 Harassment/Insults"),
        ("advert", "📢 Advertising"),
        ("cheat", "⚙️ Cheating"),
        ("nsfw", "🔞 Inappropriate content"),
        ("other", "❓ Other"),
    ],
}


async def get_lang(guild_id: int) -> str:
    lang = await db.get_language(guild_id)
    return lang if lang in STRINGS else "ru"


def tr(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in STRINGS else "ru"
    template = STRINGS[lang].get(key) or STRINGS["ru"].get(key) or key
    return template.format(**kwargs) if kwargs else template


async def t(guild_id: int, key: str, **kwargs) -> str:
    lang = await get_lang(guild_id)
    return tr(lang, key, **kwargs)
