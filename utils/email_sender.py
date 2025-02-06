import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64
from config.config_reader import load_config
from typing import Dict

def send_quiz_results(student_id, personality_type, personality_description, test_answers, signature_data):
    try:
        config = load_config()
        
        # Email settings
        smtp_server = config.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(config.get('SMTP_PORT', '587'))
        sender_email = config.get('SENDER_EMAIL', '')
        sender_password = config.get('SENDER_PASSWORD', '')
        admin_email = config.get('ADMIN_EMAIL', '')
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f'Quiz Results - Student {student_id}'
        msg['From'] = sender_email
        msg['To'] = admin_email
        
        # Create detailed results text
        text_content = f"""
        Student ID: {student_id}
        
        Personality Type: {personality_type}
        Description: {personality_description}
        
        Detailed Test Results:
        Test 1 (HIGH D) - Yes answers: {sum(1 for ans in test_answers.get('test1', []) if ans == '1')}
        Test 2 (HIGH I) - Yes answers: {sum(1 for ans in test_answers.get('test2', []) if ans == '1')}
        Test 3 (HIGH S) - Yes answers: {sum(1 for ans in test_answers.get('test3', []) if ans == '1')}
        Test 4 (HIGH C) - Yes answers: {sum(1 for ans in test_answers.get('test4', []) if ans == '1')}
        
        Please find the student's signature attached.
        """
        msg.attach(MIMEText(text_content, 'plain'))
        
        # Process and attach signature image
        if signature_data and ',' in signature_data:
            image_data = signature_data.split(',')[1]
            try:
                signature_image = base64.b64decode(image_data)
                image = MIMEImage(signature_image)
                image.add_header('Content-Disposition', 'attachment', 
                               filename=f'signature_{student_id}.jpg')
                msg.attach(image)
            except Exception as e:
                print(f"Error processing signature image: {e}")
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        return True
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_reset_email(email, reset_link):
    try:
        config = load_config()
        
        msg = MIMEMultipart()
        msg['Subject'] = 'Password Reset Request'
        msg['From'] = config.get('SENDER_EMAIL')
        msg['To'] = email
        
        text = f"""
        You have requested to reset your password.
        
        Please click the following link to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you did not request this reset, please ignore this email.
        """
        
        msg.attach(MIMEText(text, 'plain'))
        
        with smtplib.SMTP(config.get('SMTP_SERVER'), int(config.get('SMTP_PORT'))) as server:
            server.starttls()
            server.login(config.get('SENDER_EMAIL'), config.get('SENDER_PASSWORD'))
            server.send_message(msg)
            
        return True
        
    except Exception as e:
        print(f"Failed to send reset email: {e}")
        return False

def send_career_report(user_email: str, username: str, career_analysis: dict):
    """
    Sends career analysis report to admin
    """
    subject = f"Career Path Analysis Report for {username}"
    
    body = f"""
    Career Analysis Report for User: {username}
    =======================================
    
    PRIMARY CAREER RECOMMENDATION:
    {career_analysis.get('primary_recommendation', 'Not available')}
    
    ALTERNATIVE CAREER PATHS:
    {career_analysis.get('alternative_paths', 'Not available')}
    
    KEY SKILLS TO DEVELOP:
    {career_analysis.get('skill_gaps', 'Not available')}
    
    ADDITIONAL INSIGHTS:
    {career_analysis.get('additional_insights', 'Not available')}
    
    =======================================
    This analysis was generated based on the user's responses to the career assessment tests.
    """
    
    send_email(subject, body)
