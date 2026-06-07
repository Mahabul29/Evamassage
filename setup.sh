#!/bin/bash

echo "🚀 Setting up EvaMassage..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads static/uploads logs

# Set permissions
chmod 755 uploads static/uploads

# Generate secret key
SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
echo "SESSION_SECRET=$SECRET" >> .env
echo "SECRET_KEY=$SECRET" >> .env

# Initialize database
python -c "from database import user_db; user_db.init_db()"

echo "✅ Setup complete!"
echo "Run with: python app.py"
