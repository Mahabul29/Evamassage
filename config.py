import os

# Database
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///evamassage.db")
DB_NAME = "evamassage"

# Web Configuration
PORT = int(os.environ.get("PORT", 8080))
FQDN = os.environ.get("FQDN", "https://your-app.koyeb.app")

# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this")
