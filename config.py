import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'evamassage')
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'mongodb')
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
PORT = int(os.environ.get('PORT', 8080))
FQDN = os.environ.get('FQDN', 'http://localhost:8080')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
