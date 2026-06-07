from utils.email.mailer import EmailSender

email_sender = EmailSender()

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    """Handle forgot password request"""
    data = request.json
    email = data.get('email')
    
    # Find user by email
    user = user_db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "Email not found"}), 404
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user_db.save_reset_token(user['user_id'], reset_token)
    
    # Send email
    email_sender.send_password_reset(email, reset_token, user['username'])
    
    return jsonify({"success": True, "message": "Reset email sent"})

@app.route('/api/reset_password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    data = request.json
    token = data.get('token')
    new_password = data.get('new_password')
    
    user_id = user_db.verify_reset_token(token)
    if not user_id:
        return jsonify({"error": "Invalid or expired token"}), 400
    
    user_db.update_password(user_id, new_password)
    
    return jsonify({"success": True, "message": "Password updated"})
