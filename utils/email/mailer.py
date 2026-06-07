import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailSender:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('SMTP_FROM', self.smtp_user)
    
    def send_password_reset(self, to_email, reset_token, username):
        """Send password reset email"""
        subject = "Reset Your EvaMassage Password"
        reset_link = f"{os.environ.get('FQDN')}/reset_password?token={reset_token}"
        
        body = f"""
        Hello {username},
        
        We received a request to reset your password for your EvaMassage account.
        
        Click the link below to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        EvaMassage Team
        """
        
        self.send_email(to_email, subject, body)
    
    def send_welcome_email(self, to_email, username):
        """Send welcome email on registration"""
        subject = "Welcome to EvaMassage!"
        
        body = f"""
        Welcome {username}!
        
        Thank you for joining EvaMassage! You can now:
        ✅ Connect with amazing people
        ✅ Send messages and share photos
        ✅ Join group chats
        ✅ Create your profile
        
        Get started: {os.environ.get('FQDN')}/dashboard
        
        Best regards,
        EvaMassage Team
        """
        
        self.send_email(to_email, subject, body)
    
    def send_email(self, to_email, subject, body):
        """Send email using Gmail SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to Gmail SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.smtp_user, self.smtp_password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
