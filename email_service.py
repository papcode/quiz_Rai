import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config.config_reader import load_config
import os

def send_career_report(username, career_analysis):
    # Load config
    config = load_config()
    
    try:
        # Email configuration
        smtp_server = config['SMTP_SERVER']
        smtp_port = int(config['SMTP_PORT'])
        sender_email = config['SENDER_EMAIL']
        sender_password = config['SENDER_PASSWORD']
        admin_email = config['ADMIN_EMAIL']
        
        print(f"""
        Email configuration loaded:
        SMTP Server: {smtp_server}
        SMTP Port: {smtp_port}
        Sender Email: {sender_email}
        Admin Email: {admin_email}
        """)

        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = admin_email
        message["Subject"] = f"Career Analysis Report - Student: {username}"
        
        # Add email body
        body = f"""
        Career Analysis Report for {username}
        
        Please find the detailed career analysis report attached.
        
        This is an automated report from the Career Guidance System.
        """
        message.attach(MIMEText(body, "plain"))
        
        # Find and attach the latest markdown file for this user
        reports_dir = 'reports'
        files = [f for f in os.listdir(reports_dir) if f.endswith('.md')]
        if files:
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(reports_dir, x)))
            file_path = os.path.join(reports_dir, latest_file)
            
            with open(file_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype="md")
                attachment.add_header('Content-Disposition', 'attachment', filename=latest_file)
                message.attach(attachment)
        
        # Create SMTP session with logging
        print("Connecting to SMTP server...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("Starting TLS...")
            server.starttls()
            print("Logging in...")
            server.login(sender_email, sender_password)
            print("Sending email...")
            text = message.as_string()
            server.sendmail(sender_email, admin_email, text)
            print(f"Email sent successfully to admin ({admin_email})!")
            
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        print("Full error details:", e.__dict__)
        raise 