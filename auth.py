import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from config.config_reader import load_config
import re
from email_utils import send_reset_email
from itsdangerous import URLSafeTimedSerializer as Serializer  # Import Serializer for token generation
from flask import send_from_directory
from flask import current_app, send_file, abort
import pandas as pd
from werkzeug.utils import secure_filename

import os


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Load configuration
config = load_config()
mongo_uri = config['MONGO_URI']
database_name = config['DATABASE_NAME']
collection_name = config['COLLECTION_NAME']
secret_key = config['SECRET_KEY']
password_reset_salt = 'password-reset-salt'  # Define your salt

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[database_name]
    users_collection = db[collection_name]
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

# Initialize URLSafeTimedSerializer
s = Serializer(secret_key)

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if not is_valid_email(email):
            flash('Invalid email format')
            return render_template('register.html')

        try:
            if users_collection.find_one({'student_id': student_id}):
                flash('Student ID already exists')
                logger.warning(f"Registration attempt with existing Student ID: {student_id}")
                return render_template('register.html')
            if users_collection.find_one({'email': email}):
                flash('Email already exists')
                logger.warning(f"Registration attempt with existing Email: {email}")
                return render_template('register.html')
            
            # Insert the new user with the role 'student'
            users_collection.insert_one({
                'student_id': student_id,
                'email': email,
                'password': password,
                'role': 'student'  # Assign the role of student
            })
            
            flash('Registration successful! Please login.')
            logger.info(f"New user registered with Student ID: {student_id} and Email: {email}")
            return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.')
            return render_template('register.html')

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = request.form['password']
        try:
            logger.debug(f"Attempting login for Student ID: {student_id}")
            user = users_collection.find_one({'student_id': student_id})
            if user:
                logger.debug(f"User found: {user}")
                if check_password_hash(user['password'], password):
                    session['student_id'] = student_id
                    session['role'] = user.get('role')
                    logger.info(f"User logged in with Student ID: {student_id}")
                    
                    if user.get('role') == 'student':
                        return redirect(url_for('select_test'))  # Adjust to your actual quiz route
                    elif user.get('role') == 'superAdmin':
                        return redirect(url_for('auth.admin_side'))
                else:
                    logger.warning(f"Password mismatch for Student ID: {student_id}")
            else:
                logger.warning(f"No user found with Student ID: {student_id}")
            flash('Invalid credentials')
            return render_template('login.html')
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash('An error occurred during login. Please try again.')
            return render_template('login.html')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('student_id', None)
    flash('You have been logged out.')
    logger.info('User logged out.')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = users_collection.find_one({'email': email})
        if user:
            token = s.dumps(email, salt=password_reset_salt)  # Generate token
            send_reset_email(user, token)  # Pass token to send_reset_email
            flash('Password reset email sent!')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email.')
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt=password_reset_salt, max_age=3600)
    except:
        flash('The password reset link is invalid or has expired.')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', token=token)
        
        hashed_password = generate_password_hash(password)
        users_collection.update_one({'email': email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated!')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)


@auth_bp.route('/admin_side', methods=['GET'])
def admin_side():
    if 'role' in session and session['role'] == 'superAdmin':
        return render_template('admin_side.html')
    else:
        flash('Unauthorized access')
        return redirect(url_for('auth.login'))

@auth_bp.route('/download_template', methods=['GET'])
def download_template():
    try:
        # Define the file path directly in the root path
        file_path = os.path.join(current_app.root_path, 'questions.xlsx')

        # Check if the file exists
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            abort(404, description="File not found")

        # Serve the file
        return send_from_directory(directory=current_app.root_path, 
                                   path='questions.xlsx', 
                                   as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading the file: {e}")
        abort(500, description="An error occurred while downloading the file.")

@auth_bp.route('/upload_questions', methods=['POST'])
def upload_questions():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('auth.admin_side'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('auth.admin_side'))

    if file:
        file_path = os.path.join(current_app.root_path, 'questions.xlsx')
        file.save(file_path)
        flash('File uploaded and replaced successfully!')
        return redirect(url_for('auth.admin_side'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx'}