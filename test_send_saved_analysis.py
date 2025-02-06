import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from config.config_reader import load_config

def send_saved_analysis(json_file_path):
    # Load the saved data
    print(f"Reading data from: {json_file_path}")
    with open(json_file_path, 'r') as f:
        data = json.load(f)
        
    # Load email config
    config = load_config()
    
    # Email configuration
    smtp_server = config['SMTP_SERVER']
    smtp_port = int(config['SMTP_PORT'])
    sender_email = config['SENDER_EMAIL']
    sender_password = config['SENDER_PASSWORD']
    admin_email = config['ADMIN_EMAIL']
    
    print(f"""
    Email configuration:
    SMTP Server: {smtp_server}
    SMTP Port: {smtp_port}
    Sender Email: {sender_email}
    Admin Email: {admin_email}
    """)
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = admin_email
        message["Subject"] = f"Career Analysis Report - Student: {data['username']}"
        
        body = f"""
        Career Analysis Report
        ---------------------
        Student Username: {data['username']}
        Timestamp: {data['timestamp']}
        
        Analysis Results:
        ----------------
        {data['career_analysis']}
        
        This is an automated report from the Career Guidance System.
        """
        
        message.attach(MIMEText(body, "html"))
        
        # Create SMTP session
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

def list_saved_analyses():
    """List all saved analysis files in the logs directory"""
    if not os.path.exists('logs'):
        print("No logs directory found!")
        return []
    
    files = [f for f in os.listdir('logs') if f.startswith('career_analysis_') and f.endswith('.json')]
    return files

if __name__ == "__main__":
    # List all saved analyses
    print("Available analysis files:")
    files = list_saved_analyses()
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    
    if files:
        try:
            # Let user select which file to send
            selection = int(input("\nEnter the number of the file to send (0 to exit): "))
            if 0 < selection <= len(files):
                file_path = os.path.join('logs', files[selection-1])
                print(f"\nSending analysis from {file_path}")
                send_saved_analysis(file_path)
            else:
                print("Invalid selection")
        except ValueError:
            print("Please enter a valid number")
    else:
        print("No saved analysis files found") 