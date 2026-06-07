import os
from pymongo import MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'evamassage')
SECRET_KEY = 'your-secret-key-12345'
PORT = int(os.environ.get('PORT', 8080))

# Database connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users = db['users']
messages = db['messages']
chats = db['chats']
channels = db['channels']
channel_members = db['channel_members']
channel_msgs = db['channel_messages']
