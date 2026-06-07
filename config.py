import os

# Database - Use PostgreSQL on Koyeb, SQLite for local
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///evamassage.db")
DB_NAME = "evamassage"

# Admin Configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# Web Configuration
PORT = int(os.environ.get("PORT", 8080))
FQDN = os.environ.get("FQDN", "https://your-app.koyeb.app")
APP_URL = os.environ.get("APP_URL", FQDN)

# Security
SESSION_SECRET = os.environ.get("SESSION_SECRET", "your-secret-key-change-this")
SECRET_KEY = os.environ.get("SECRET_KEY", SESSION_SECRET)

# Upload settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'pdf'}

# Pagination
USERS_PER_PAGE = 20
MESSAGES_PER_PAGE = 50
