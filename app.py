from flask import Flask, render_template, session, redirect, send_from_directory
from config import SECRET_KEY, PORT, users  # Imported users collection directly for real-time lookups
from routes.auth import auth_bp
from routes.user_routes import user_bp
from routes.message_routes import msg_bp
from routes.channel_routes import channel_bp
from routes.call_routes import call_bp
from routes.file_routes import file_bp
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register all application feature blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(msg_bp)
app.register_blueprint(channel_bp)
app.register_blueprint(call_bp)
app.register_blueprint(file_bp)

# ── Static File Routing ───────────────────────────────────────────────────────

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

# ── Core Page Routing ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Root route: Redirect to dashboard if logged in, otherwise present login page."""
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Main communication dashboard window."""
    if 'user_id' not in session:
        return redirect('/')
        
    # Fetch latest user state parameters to ensure names/avatars look clean live
    current_user = users.find_one({'user_id': session['user_id']})
    if not current_user:
        return redirect('/logout') # Safety fallback if database drops record
        
    return render_template('index.html', user=current_user)

@app.route('/profile')
def profile():
    """Legacy profile route. Redirects to unified new modular settings panel."""
    if 'user_id' not in session:
        return redirect('/')
    return redirect('/settings')

@app.route('/settings')
def settings():
    """
    Unified account settings controller.
    Loads real-time bio, username, avatar definitions, and current system credentials.
    """
    if 'user_id' not in session:
        return redirect('/')
        
    # Query database directly instead of reliance on temporary static sessions
    current_user = users.find_one({'user_id': session['user_id']})
    if not current_user:
        return redirect('/')
        
    return render_template('settings.html', user=current_user)

# ── Application Runtime Execution ─────────────────────────────────────────────

if __name__ == '__main__':
    # Starts server using configurations extracted cleanly out of your configuration file
    app.run(host='0.0.0.0', port=PORT, debug=True)
    
