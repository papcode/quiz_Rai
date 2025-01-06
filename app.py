from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import configparser
import openpyxl
import json
from config.config_reader import load_config
from auth import auth_bp  # Import the auth Blueprint

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

@app.route('/')
def select_test():
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))
    test_names = get_test_names('questions.xlsx')
    return render_template('select_test.html', test_names=test_names)

@app.route('/test/<test_name>', methods=['GET', 'POST'])
def test(test_name):
    if 'student_id' not in session:
        return redirect(url_for('auth.login'))
    
    questions = load_questions('questions.xlsx', test_name)
    results = {}
    retry_mode = False
    is_easy_mode = request.args.get('easy_mode', 'false') == 'true'
    
    # Initialize shown questions tracking if not exists
    if 'shown_easy_questions' not in session:
        session['shown_easy_questions'] = []
    
    if request.method == 'POST':
        user_answers = request.form.to_dict()
        incorrect_questions = []

        # Get the current questions based on mode
        current_questions = session.get('easy_questions', questions) if is_easy_mode else questions

        for question in current_questions:
            question_text = question['question']
            user_answer = user_answers.get(question_text, '').strip()
            correct_answer = str(question['answer']).strip()

            is_correct = user_answer.lower() == correct_answer.lower()
            if not is_correct:
                incorrect_questions.append(question_text)

            results[question_text] = {
                'user_answer': user_answer,
                'is_correct': is_correct,
                'correct_answer': correct_answer
            }

        if not incorrect_questions:
            # Clear all session data when all answers are correct
            session.pop('easy_questions', None)
            session.pop('shown_easy_questions', None)
            return redirect(url_for('congratulations'))

        # Load new easy questions for incorrect answers
        new_easy_questions = []
        shown_questions = session['shown_easy_questions']
        
        # Get all available easy questions
        all_easy_questions = load_easy_questions('questions.xlsx', float('inf'))
        
        # Filter out previously shown questions
        available_questions = [q for q in all_easy_questions 
                             if q['question'] not in shown_questions]
        
        # Randomly select required number of new questions
        import random
        num_needed = len(incorrect_questions)
        if available_questions:
            selected_questions = random.sample(available_questions, 
                                            min(num_needed, len(available_questions)))
            new_easy_questions.extend(selected_questions)
            
            # Update shown questions list
            session['shown_easy_questions'].extend(q['question'] for q in selected_questions)
            
        session['easy_questions'] = new_easy_questions
        return redirect(url_for('test', test_name=test_name, easy_mode='true'))

    if is_easy_mode:
        questions = session.get('easy_questions', [])
        return render_template('index.html', 
                             questions=questions, 
                             test_name=test_name, 
                             results={}, 
                             retry_mode=False, 
                             user_answers={},
                             is_easy_mode=True)

    # Clear session data when starting a new test
    session.pop('easy_questions', None)
    session.pop('shown_easy_questions', None)
    return render_template('index.html', 
                         questions=questions, 
                         test_name=test_name, 
                         results=results, 
                         retry_mode=retry_mode, 
                         user_answers={},
                         is_easy_mode=False)

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
