from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from config.config_reader import load_config

def test_email_service():
    # Load config
    config = load_config()
    
    # Email configuration
    smtp_server = config['SMTP_SERVER']
    smtp_port = int(config['SMTP_PORT'])
    sender_email = config['SENDER_EMAIL']
    sender_password = config['SENDER_PASSWORD']
    
    # Test recipient (you can change this to your email)
    test_recipient = "navneezme@gmail.com"  # or use config['ADMIN_EMAIL']
    
    print(f"""
    Testing email configuration:
    SMTP Server: {smtp_server}
    SMTP Port: {smtp_port}
    Sender Email: {sender_email}
    Recipient Email: {test_recipient}
    """)
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = test_recipient
        message["Subject"] = "Test Email from Career Guidance System"
        
        body = """
        This is a test email from the Career Guidance System.
        
        If you receive this, the email service is working correctly.
        
        Best regards,
        System Test
        """
        
        message.attach(MIMEText(body, "plain"))
        
        # Create SMTP session
        print("Connecting to SMTP server...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("Starting TLS...")
            server.starttls()
            print("Logging in...")
            server.login(sender_email, sender_password)
            print("Sending email...")
            text = message.as_string()
            server.sendmail(sender_email, test_recipient, text)
            print("Email sent successfully!")
            
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        print("Full error details:", e.__dict__)

if __name__ == "__main__":
    test_email_service() 