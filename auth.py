import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from config.config_reader import load_config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Load configuration
config = load_config()
mongo_uri = config['MONGO_URI']
database_name = config['DATABASE_NAME']
collection_name = config['COLLECTION_NAME']

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # Set a 5-second timeout
    db = client[database_name]
    users_collection = db[collection_name]
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = generate_password_hash(request.form['password'])
        try:
            if users_collection.find_one({'student_id': student_id}):
                flash('Student ID already exists')
                logger.warning(f"Registration attempt with existing Student ID: {student_id}")
                return render_template('register.html')
            users_collection.insert_one({'student_id': student_id, 'password': password})
            flash('Registration successful! Please login.')
            logger.info(f"New user registered with Student ID: {student_id}")
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
            user = users_collection.find_one({'student_id': student_id})
            if user and check_password_hash(user['password'], password):
                session['student_id'] = student_id
                logger.info(f"User logged in with Student ID: {student_id}")
                return redirect(url_for('select_test'))  # Adjust to your actual quiz route
            flash('Invalid credentials')
            logger.warning(f"Login failed for Student ID: {student_id}")
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
    logger.info("User logged out")
    return redirect(url_for('auth.login'))
