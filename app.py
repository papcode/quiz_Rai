from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from auth import auth_bp
from database import users_collection
from config.config_reader import load_config
from utils.email_sender import send_quiz_results, send_career_report
from services.llm_service import LLMService
import openpyxl
import os
import json
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Load configuration
config = load_config()
app.secret_key = config['SECRET_KEY']

# Register blueprints
app.register_blueprint(auth_bp)

# Initialize LLM service
llm_service = LLMService(config['BASE_URL'])

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    user = users_collection.find_one({'student_id': session['username']})
    if not user:
        return redirect(url_for('auth.login'))
    
    # If no signature, redirect to canvas
    if not user.get('signature'):
        return redirect(url_for('canvas_name'))
    
    # If quiz is completed, show completion page
    if user.get('quiz_completed'):
        return redirect(url_for('completion'))
    
    # Otherwise, go to test selection/first test
    return redirect(url_for('test', test_number=1))

@app.route('/canvas_name')
def canvas_name():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    return render_template('canvas_name.html')

@app.route('/save_signature', methods=['POST'])
def save_signature():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    try:
        data = request.get_json()
        signature_data = data.get('signature')
        
        if not signature_data:
            return jsonify({'success': False, 'error': 'No signature data'})
        
        # Update user's signature in database
        users_collection.update_one(
            {'student_id': session['username']},
            {'$set': {'signature': signature_data}}
        )
        
        return jsonify({
            'success': True,
            'redirect_url': url_for('test', test_number=1)
        })
        
    except Exception as e:
        print(f"Error saving signature: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reset_signature', methods=['POST'])
def reset_signature():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    # Reset the signature in the database
    users_collection.update_one(
        {'student_id': session['username']},
        {'$set': {'signature': None}}
    )
    
    # Redirect to canvas page
    return redirect(url_for('canvas_name'))

@app.route('/test/<int:test_number>', methods=['GET', 'POST'])
def test(test_number):
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        # Read questions from Excel using the correct column name: "Question"
        df = pd.read_excel('questions.xlsx', sheet_name=f'TEST{test_number}')
        questions = [{"question": q} for q in df['Question'].tolist()]
        
        return render_template('test.html', 
                             test_number=test_number,
                             questions=questions)

    # For POST requests
    try:
        # Get form data
        form_data = request.form
        responses = []
        
        # Process each answer from the form
        for i in range(len(form_data)):
            answer_key = f'answers[{i}]'
            if answer_key in form_data:
                responses.append(form_data[answer_key])
        
        print(f"Received responses for test {test_number}:", responses)
        
        # Store responses in session
        session[f'test{test_number}_responses'] = responses
        
        # Determine next action
        if test_number < 4:
            next_test = test_number + 1
            return redirect(url_for('test', test_number=next_test))
        else:
            return redirect(url_for('submit'))
            
    except Exception as e:
        print(f"Error saving test responses: {str(e)}")
        flash('An error occurred while saving your responses. Please try again.')
        return redirect(url_for('test', test_number=test_number))

@app.route('/results')
def results():
    # Redirect to the new completion page
    return redirect(url_for('completion'))

@app.route('/test/<int:test_number>', methods=['POST'])
def submit_test(test_number):
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        # Get responses from request
        responses = request.get_json()
        print(f"Received responses for test {test_number}:", responses)
        
        # Store responses in session
        session[f'test{test_number}_responses'] = responses
        
        # Set response headers for redirect
        if test_number < 4:
            response = Response()
            response.headers['Location'] = url_for('test', test_number=test_number + 1)
            response.status_code = 302  # HTTP redirect status code
            return response
        else:
            response = Response()
            response.headers['Location'] = url_for('submit')
            response.status_code = 302
            return response
        
    except Exception as e:
        print(f"Error saving test responses: {str(e)}")
        flash('An error occurred while saving your responses.')
        return redirect(url_for('test', test_number=test_number))

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        username = session.get('username')
        print(f"Processing career analysis for username: {username}")
        
        # Collect all test responses
        test_responses = {
            f'TEST{i}': session.get(f'test{i}_responses', [])
            for i in range(1, 5)
        }
        
        print(f"Collected responses: {test_responses}")
        
        # Get career analysis
        try:
            base_url = config['BASE_URL']
            llm_service = LLMService(base_url)
            career_analysis = llm_service.get_career_analysis(test_responses)
            print("Career analysis completed successfully")
            
            # Save data to JSON file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_to_save = {
                "timestamp": timestamp,
                "username": username,
                "test_responses": test_responses,
                "career_analysis": career_analysis
            }
            
            # Create logs directory if it doesn't exist
            if not os.path.exists('logs'):
                os.makedirs('logs')
            
            # Save to JSON file
            filename = f"logs/career_analysis_{username}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            print(f"Data saved to {filename}")
            
            # Send email using the same mechanism as test script
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
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = admin_email
            message["Subject"] = f"Career Analysis Report - Student: {username}"
            
            body = f"""
            Career Analysis Report
            ---------------------
            Student Username: {username}
            Timestamp: {timestamp}
            
            Analysis Results:
            ----------------
            {career_analysis}
            
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
            print(f"Error in analysis or email: {e}")
            print("Full error details:", e.__dict__)
            raise
        
        # Update user status
        users_collection.update_one(
            {'student_id': username},
            {'$set': {'quiz_completed': True}}
        )
        
        # Store analysis in session
        session['career_analysis'] = career_analysis
        
        return redirect(url_for('completion'))
        
    except Exception as e:
        print(f"Error in submission process: {str(e)}")
        flash('An error occurred while processing your responses. Please try again.')
        return redirect(url_for('home'))

@app.route('/completion')
def completion():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    career_analysis = session.get('career_analysis', {})
    return render_template('completion.html', career_analysis=career_analysis)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.')
    return redirect(url_for('auth.login'))

# Helper functions for loading questions and calculating personality type
def load_questions(file_path, sheet_name):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook[sheet_name]
    questions = []
    
    # Assuming questions are in column A starting from row 2
    for row in sheet.iter_rows(min_row=2):
        if row[0].value:  # Check if there's a question in column A
            questions.append({
                'question': row[0].value,
            })
    return questions

def calculate_personality_type(test_answers):
    if not test_answers:
        return "Unknown"
    
    # Count 'yes' answers (value '1') for each test
    yes_counts = {
        'test1': 0,  # HIGH D
        'test2': 0,  # HIGH I
        'test3': 0,  # HIGH S
        'test4': 0   # HIGH C
    }
    
    personality_types = {
        'test1': {
            'type': 'HIGH D',
            'description': ('Extroverted + Task Oriented: Ambitious, Forcefull, Decisive, Direct, '
                          'Independent, Challenging, Results oriented, I have a desire to win, '
                          'Argumentative, Fast paced, I tend to juggle a lot at once, '
                          'I am quick to accept challenge, I usually interrupt and am impatient with '
                          'long explanations, I tend to act or speak before thinking, I am not afraid '
                          'of high risk, I tend to create fear in others, I tend to be impatient')
        },
        'test2': {
            'type': 'HIGH I',
            'description': ('Extroverted + People Oriented: Expressive, Enthusiastic, Friendly, '
                          'Demonstrative, Talkative, Stimulating, I have a good sense of humor, '
                          'I treat everyone as a friend, I am fun loving, I am a creative problem solver, '
                          'I am usually very optimistic, I tend to talk before thinking, I very often '
                          'lose track of time, I prefer to back away from conflict, I tend to be '
                          'disorganized, I am very trusting of others')
        },
        'test3': {
            'type': 'HIGH S',
            'description': ('Introverted + People Oriented: Methodical, Systematic, Reliable, Steady, '
                          'Relaxed, Modest, I need secure situations, I am a good planner, I need closure, '
                          'I am a great listener, I am usually calm and stabilize others, I mask my emotions, '
                          'I tend to be indirect to avoid conflict, I tend to be possessive of things, '
                          'I tend to be too low risk, I tend to hold a grudge, I tend to adapt very '
                          'quickly to others, I tend to resist changes')
        },
        'test4': {
            'type': 'HIGH C',
            'description': ('Introverted + Task Oriented: Analytical, Contemplative, Conservative, '
                          'Exacting, Careful, Deliberate, I like to organize and analyze, I work well '
                          'alone, I have high expectations, I like to follow rules, I am self-competitive, '
                          'I can solve complex problems, I live my life by rules of behaving, I tend to '
                          'want as much data as possible, I tend to be hard on myself, I never take '
                          'unnecessary chances, I tend to feel emotions are very irrational, I tend to '
                          'see faults in others, I tend to analyze things to death')
        }
    }
    
    # Count yes answers for each test
    for test_num, answers in test_answers.items():
        yes_count = sum(1 for ans in answers if ans == '1')
        yes_counts[test_num] = yes_count
    
    # Find the test with the highest yes count
    max_yes_test = max(yes_counts.items(), key=lambda x: x[1])[0]
    
    # Return the corresponding personality type and description
    return personality_types[max_yes_test]

if __name__ == '__main__':
    app.run(debug=True)
