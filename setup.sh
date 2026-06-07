#!/bin/bash
pip install -r requirements.txt
python -c "from app import init_db; init_db()"
echo "Setup complete! Run: python app.py"
