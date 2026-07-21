import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")

# ID сервера для быстрой синхронизации слэш-команд (необязательно).
# Если указать GUILD_ID, команды появятся на сервере почти мгновенно.
# Если оставить пустым, синхронизация будет глобальной (до 1 часа).
GUILD_ID = os.getenv("GUILD_ID", "")

# Юзернейм поддержки, который выводится в /support
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@Ikromdjon")

DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# Discord ID владельца бота — только этому пользователю видна команда /webapp
OWNER_ID = os.getenv("OWNER_ID", "")

# Домены-исключения для антиспам-фильтра ссылок (например, ссылки на discord.gg
# вашего же сервера, если хотите их разрешить — добавьте отдельно в БД через /links).
