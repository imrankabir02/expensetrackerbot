import os

# Bot token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8298302907:AAEh16HAggOwbVlVN59KuJ5C3tCBQoMSDyU")

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///expenses.db")
