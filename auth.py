from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import users_collection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = generate_password_hash(request.form['password'])
        if users_collection.find_one({'student_id': student_id}):
            flash('Student ID already exists')
            return render_template('register.html')
        
        # Create user with initial fields
        users_collection.insert_one({
            'student_id': student_id,
            'password': password,
            'signature': None,  # Initialize signature as None
            'test_answers': {}  # Initialize empty test answers
        })
        
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
            session.clear()
            session['username'] = student_id
            
            # Check if user has signature
            if not user.get('signature'):
                return redirect(url_for('canvas_name'))
            else:
                return redirect(url_for('home'))
                
        flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear all session data
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))
