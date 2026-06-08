from flask import Flask, render_template, session, redirect, send_from_directory
from config import SECRET_KEY, PORT
from routes.auth import auth_bp
from routes.user_routes import user_bp
from routes.message_routes import msg_bp
from routes.channel_routes import channel_bp
from routes.call_routes import call_bp
from routes.file_routes import file_bp
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(channel_bp)
app.register_blueprint(call_bp)
app.register_blueprint(file_bp)

# Static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

# Page routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('index.html', user=session)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('profile.html')

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('settings.html', user=session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    print(f"🚀 Server running on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
    
