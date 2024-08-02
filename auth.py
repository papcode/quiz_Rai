from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from config.config_reader import load_config

auth_bp = Blueprint('auth', __name__)

# Load configuration
config = load_config()
mongo_uri = config['MONGO_URI']
database_name = config['DATABASE_NAME']
collection_name = config['COLLECTION_NAME']

client = MongoClient(mongo_uri)
db = client[database_name]
users_collection = db[collection_name]

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = generate_password_hash(request.form['password'])
        if users_collection.find_one({'student_id': student_id}):
            flash('Student ID already exists')
            return render_template('register.html')
        users_collection.insert_one({'student_id': student_id, 'password': password})
        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = request.form['password']
        user = users_collection.find_one({'student_id': student_id})
        if user and check_password_hash(user['password'], password):
            session['student_id'] = student_id
            return redirect(url_for('select_test'))  # Adjust to your actual quiz route
        flash('Invalid credentials')
        return render_template('login.html')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('student_id', None)
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))
