from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import users_collection
from bson.objectid import ObjectId
import secrets
from datetime import datetime, timedelta
from utils.email_sender import send_reset_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form['student_id']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        if users_collection.find_one({'$or': [
            {'student_id': student_id},
            {'email': email}
        ]}):
            flash('Student ID or Email already registered')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = {
            'student_id': student_id,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.utcnow()
        }
        users_collection.insert_one(user)
        
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

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = users_collection.find_one({'email': email})
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            
            # Store reset token
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {
                    'reset_token': token,
                    'reset_token_expiry': expiry
                }}
            )
            
            # Send reset email
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            send_reset_email(email, reset_link)
            
            flash('Password reset instructions sent to your email')
            return redirect(url_for('auth.login'))
        
        flash('Email not found')
        return redirect(url_for('auth.forgot_password'))
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = users_collection.find_one({
        'reset_token': token,
        'reset_token_expiry': {'$gt': datetime.utcnow()}
    })
    
    if not user:
        flash('Invalid or expired reset link')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('auth.reset_password', token=token))
        
        # Update password and remove reset token
        users_collection.update_one(
            {'_id': user['_id']},
            {
                '$set': {'password': generate_password_hash(password)},
                '$unset': {'reset_token': '', 'reset_token_expiry': ''}
            }
        )
        
        flash('Password has been reset successfully')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html')

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email')
    exists = users_collection.find_one({'email': email}) is not None
    return jsonify({'exists': exists})

@auth_bp.route('/check-student-id', methods=['POST'])
def check_student_id():
    data = request.get_json()
    student_id = data.get('student_id')
    exists = users_collection.find_one({'student_id': student_id}) is not None
    return jsonify({'exists': exists})
