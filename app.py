from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from auth import auth_bp
from database import users_collection
from config.config_reader import load_config
from utils.email_sender import send_quiz_results
import openpyxl
import os
import json

app = Flask(__name__)

# Load configuration
config = load_config()
app.secret_key = config['SECRET_KEY']

# Register blueprints
app.register_blueprint(auth_bp)

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
    
    # If quiz is completed, show results
    if user.get('quiz_completed'):
        return redirect(url_for('results'))
    
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
    
    user = users_collection.find_one({'student_id': session['username']})
    if not user or not user.get('signature'):
        return redirect(url_for('canvas_name'))
    
    if test_number < 1 or test_number > 4:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        # Get all answers from the form
        answers = []
        for key in sorted(request.form.keys()):  # Sort to maintain order
            if key.startswith('answers['):
                answers.append(request.form[key])
        
        if 'test_answers' not in session:
            session['test_answers'] = {}
        session['test_answers'][f'test{test_number}'] = answers
        
        # Update user's progress in database
        users_collection.update_one(
            {'student_id': session['username']},
            {'$set': {f'test_answers.test{test_number}': answers}}
        )
        
        if test_number < 4:
            return jsonify({'next_url': url_for('test', test_number=test_number + 1)})
        else:
            users_collection.update_one(
                {'student_id': session['username']},
                {'$set': {'quiz_completed': True}}
            )
            return jsonify({'next_url': url_for('results')})
    
    try:
        questions = load_questions('questions.xlsx', f'TEST{test_number}')
        if not questions:
            raise Exception("No questions found")
            
        return render_template('test.html', questions=questions)
    except Exception as e:
        print(f"Error loading questions: {e}")
        flash("Error loading questions. Please try again.")
        return redirect(url_for('home'))

@app.route('/results')
def results():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        user = users_collection.find_one({'student_id': session['username']})
        if not user:
            return redirect(url_for('auth.login'))

        # Get all test answers and signature
        test_answers = user.get('test_answers', {})
        signature_data = user.get('signature', '')
        
        # Calculate personality type
        personality_result = calculate_personality_type(test_answers)
        
        # Send email to admin with detailed results
        email_sent = send_quiz_results(
            student_id=session['username'],
            personality_type=personality_result['type'],
            personality_description=personality_result['description'],
            test_answers=test_answers,
            signature_data=signature_data
        )
        
        if not email_sent:
            print("Failed to send email to admin")
            flash("There was an error processing your results. Please contact administrator.")
            return redirect(url_for('home'))
        
        return render_template('completion.html')
                             
    except Exception as e:
        print(f"Error in results route: {e}")
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
