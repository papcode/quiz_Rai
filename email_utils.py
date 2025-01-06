from flask_mail import Mail, Message
from flask import current_app, url_for

def init_email_utils(app):
    # Initialize Mail instance
    mail = Mail(app)
    return mail

def send_reset_email(user, token):  # Accept token as parameter
    mail = current_app.extensions['mail']
    msg = Message('Password Reset Request', sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[user['email']])
    link = url_for('auth.reset_password', token=token, _external=True)  # Ensure url_for is imported
    msg.body = f'Your password reset link is {link}'
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")





