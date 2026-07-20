import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = os.getenv("GUILD_ID", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@Ikromdjon")
DB_PATH = os.getenv("DB_PATH", "bot_database.db")
OWNER_ID = os.getenv("OWNER_ID", "")
WEBPANEL_PASSWORD = os.getenv("WEBPANEL_PASSWORD", "")
WEBPANEL_SECRET_KEY = os.getenv("WEBPANEL_SECRET_KEY", "change-me-please")
