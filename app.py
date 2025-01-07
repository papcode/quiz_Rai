from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import configparser
import openpyxl
import json
from config.config_reader import load_config
from auth import auth_bp  # Import the auth Blueprint

#CHANGES

config = load_config()
mongo_uri = config['MONGO_URI']
database_name = config['DATABASE_NAME']
collection_name = config['COLLECTION_NAME']
secret_key = config['SECRET_KEY']

app = Flask(__name__)
app.secret_key = secret_key

client = MongoClient(mongo_uri)
db = client[database_name]
users_collection = db[collection_name]

app.register_blueprint(auth_bp)  # Register the auth Blueprint

# Load the sheet names from the Excel file
def get_test_names(filename):
    workbook = openpyxl.load_workbook(filename, data_only=True)
    return [sheet for sheet in workbook.sheetnames if sheet.startswith("TEST")]

# Load the questions from the Excel file
def load_questions(filename, sheet_name):
    workbook = openpyxl.load_workbook(filename, data_only=True)
    sheet = workbook[sheet_name]
    questions = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        question_text = row[0]
        answer_text = row[1]
        if question_text and answer_text:  # Check if both question and answer are present
            questions.append({'question': question_text, 'answer': answer_text})
    return questions

# Add this new function
def load_easy_questions(filename, num_questions):
    workbook = openpyxl.load_workbook(filename, data_only=True)
    if 'easy_set' not in workbook.sheetnames:
        return []
    
    sheet = workbook['easy_set']
    all_easy_questions = []
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        question_text = row[0]
        answer_text = row[1]
        if question_text and answer_text:
            all_easy_questions.append({'question': question_text, 'answer': answer_text})
    
    # Randomly select the required number of questions
    import random
    return random.sample(all_easy_questions, min(num_questions, len(all_easy_questions)))

def determine_personality(test_answers):
    personality_scores = {
        'HIGH D': sum(1 for ans in test_answers['test1'] if ans == 'yes'),
        'HIGH I': sum(1 for ans in test_answers['test2'] if ans == 'yes'),
        'HIGH S': sum(1 for ans in test_answers['test3'] if ans == 'yes'),
        'HIGH C': sum(1 for ans in test_answers['test4'] if ans == 'yes')
    }
    return max(personality_scores.items(), key=lambda x: x[1])[0]

@app.route('/')
def home():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('test', test_number=1))

@app.route('/test/<int:test_number>', methods=['GET', 'POST'])
def test(test_number):
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))
    
    if test_number < 1 or test_number > 4:
        return redirect(url_for('test', test_number=1))
    
    # Load questions for the current test
    sheet_name = f'TEST{test_number}'
    questions = load_questions('questions.xlsx', sheet_name)
    
    if request.method == 'POST':
        # Process answers
        answers = {q['question']: request.form.get(q['question']) for q in questions}
        
        # Store answers in session
        if 'test_answers' not in session:
            session['test_answers'] = {}
        session['test_answers'][f'test{test_number}'] = answers
        
        # If this was the last test, go to results
        if test_number == 4:
            return redirect(url_for('results'))
        
        # Otherwise, go to next test
        return redirect(url_for('test', test_number=test_number + 1))
    
    return render_template('index.html', questions=questions)

@app.route('/results')
def results():
    if 'student_id' not in session or 'test_answers' not in session:
        return redirect(url_for('auth.login'))
    
    # Calculate personality type based on answers
    test_answers = session['test_answers']
    personality_scores = {
        'HIGH D': sum(1 for ans in test_answers.get('TEST1', []) if ans == 'yes'),
        'HIGH I': sum(1 for ans in test_answers.get('TEST2', []) if ans == 'yes'),
        'HIGH S': sum(1 for ans in test_answers.get('TEST3', []) if ans == 'yes'),
        'HIGH C': sum(1 for ans in test_answers.get('TEST4', []) if ans == 'yes')
    }
    
    # Get the personality type with the highest score
    personality_type = max(personality_scores.items(), key=lambda x: x[1])[0]
    
    # Clear the test answers from session
    session.pop('test_answers', None)
    
    return render_template('results.html', personality_type=personality_type)

@app.route('/error_page')
def error_page():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))

    incorrect_count = request.args.get('incorrect_count', 0, type=int)
    test_name = request.args.get('test_name', '')
    user_answers = request.args.get('user_answers', '{}')

    # Pass JSON encoded user_answers
    return render_template('error_page.html', incorrect_count=incorrect_count, test_name=test_name, user_answers=user_answers)

@app.route('/congratulations')
def congratulations():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('congratulations.html')

if __name__ == '__main__':
    app.run(debug=True)
