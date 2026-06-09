from flask import Flask, render_template, session, redirect, send_from_directory
from config import SECRET_KEY, PORT
from routes.auth import auth_bp
from models.user import user_bp  
from routes.message_routes import msg_bp
from routes.channel_routes import channel_bp
from routes.call_routes import call_bp
from routes.file_routes import file_bp
from config import db
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

# Static files directory
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# CRITICAL PWA FIX: Served publicly from root with zero-cache to prevent login redirects
@app.route('/sw.js')
def service_worker():
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/manifest.json')
def manifest():
    response = send_from_directory('static', 'manifest.json', mimetype='application/json')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Page routing views
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user = db['users'].find_one({'user_id': session['user_id']})
    if user:
        session['full_name'] = user.get('full_name', session.get('full_name', ''))
        session['username'] = user.get('username', session.get('username', ''))
    return render_template('index.html', user=session)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/')
    user = db['users'].find_one({'user_id': session['user_id']})
    if not user:
        return redirect('/')
    user.setdefault('avatar', 'default')
    user.setdefault('language', 'en')
    user.setdefault('theme', 'light')
    user.setdefault('text_size', 'medium')
    user.setdefault('auto_delete', 'never')
    return render_template('profile.html', profile=user, user=user)

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect('/')
    user = db['users'].find_one({'user_id': session['user_id']})
    if not user:
        return redirect('/')
    user.setdefault('theme', 'light')
    return render_template('settings.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    print(f"🚀 Server running on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
    
