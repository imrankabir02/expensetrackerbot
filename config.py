import os
from dotenv import load_dotenv

load_dotenv()

# Bot token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL")
