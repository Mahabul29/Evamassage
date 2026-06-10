from flask import Flask, render_template, session, redirect, send_from_directory
from config import SECRET_KEY, PORT, db
from routes.auth import auth_bp
from models.user import user_bp
from routes.message_routes import msg_bp
from routes.channel_routes import channel_bp
from routes.channel_settings_routes import channel_settings_bp
from routes.call_routes import call_bp
from routes.file_routes import file_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(channel_bp)
app.register_blueprint(channel_settings_bp, url_prefix='/api')
app.register_blueprint(call_bp)
app.register_blueprint(file_bp)

# ... rest of your routes ...

if __name__ == '__main__':
    print(f"🚀 Server running on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
