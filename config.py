import os
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
load_dotenv()

# ============================================
# APPLICATION CONFIGURATION
# ============================================

# Flask Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
SESSION_SECRET = os.environ.get('SESSION_SECRET', SECRET_KEY)

# Server Configuration
PORT = int(os.environ.get('PORT', 8080))
FQDN = os.environ.get('FQDN', 'https://your-app.koyeb.app')
APP_URL = os.environ.get('APP_URL', FQDN)

# Debug Mode (set to False in production)
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# ============================================
# MONGODB CONFIGURATION
# ============================================

# MongoDB Connection URI
# Format for MongoDB Atlas:
# mongodb+srv://username:password@cluster.mongodb.net/database_name?retryWrites=true&w=majority
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'evamassage')

# Database type: 'mongodb' or 'sqlite'
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'mongodb')

# SQLite fallback (if MongoDB is not available)
SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', 'evamassage.db')

# ============================================
# ADMIN CONFIGURATION
# ============================================

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ============================================
# FILE UPLOAD CONFIGURATION
# ============================================

MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10MB
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,mp4,pdf').split(',')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')

# ============================================
# RATE LIMITING
# ============================================

RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
RATE_LIMIT = int(os.environ.get('RATE_LIMIT', 100))
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))

# ============================================
# MAINTENANCE MODE
# ============================================

MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', 'Under maintenance. Please check back later.')

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_mongo_uri():
    """Get MongoDB URI with error checking"""
    uri = MONGO_URI
    if not uri or uri == 'mongodb://localhost:27017/':
        print("⚠️ Warning: Using default MongoDB URI. Set MONGO_URI environment variable.")
    return uri

def is_production():
    """Check if running in production"""
    return not DEBUG and FQDN != 'https://your-app.koyeb.app'

if __name__ == '__main__':
    print("=" * 50)
    print("EvaMassage Configuration")
    print("=" * 50)
    print(f"Database Type: {DATABASE_TYPE}")
    print(f"MongoDB URI: {get_mongo_uri()[:50]}...")
    print(f"MongoDB Database: {MONGO_DB_NAME}")
    print(f"Port: {PORT}")
    print(f"FQDN: {FQDN}")
    print(f"Debug Mode: {DEBUG}")
    print(f"Rate Limit: {RATE_LIMIT} per {RATE_LIMIT_WINDOW}s")
    print(f"Maintenance Mode: {MAINTENANCE_MODE}")
    print("=" * 50)
