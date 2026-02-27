"""
Authentication routes for Online Exam Proctoring System
Handles login, logout, and signup
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os

auth_bp = Blueprint('auth', __name__)

# Database configuration
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'proctor')
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@auth_bp.route('/')
def home():
    """Redirect to login page"""
    return redirect(url_for('auth.unified_login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def unified_login():
    """Unified login page - automatically detects user type"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"\n🔐 Auto-detect Login Attempt:")
        print(f"  Username: {username}")
        
        if not username or not password:
            flash("Please fill in all fields", "error")
            return redirect(url_for('auth.unified_login'))
        
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            
            # Try Admin first
            query = "SELECT admin_id, username, password FROM admin WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            
            if result and check_password_hash(result[2], password):
                session['admin_id'] = result[0]
                session['admin_username'] = result[1]
                print(f"  ✓ Logged in as Admin (ID: {result[0]})\n")
                return redirect(url_for('admin.admin_dashboard'))
            
            # Try Teacher
            query = "SELECT authority_id, username, password FROM exam_authority WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            
            if result and check_password_hash(result[2], password):
                session['authority_id'] = result[0]
                session['username'] = result[1]
                print(f"  ✓ Logged in as Teacher\n")
                return redirect(url_for('teacher.teacher_dashboard'))
            
            # Try Student
            query = "SELECT user_id, username, password, session_id FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            
            if result:
                if check_password_hash(result[2], password):
                    # Force logout from previous session and create new one
                    session_id = str(uuid.uuid4())
                    session['user_id'] = result[0]
                    session['username'] = result[1]
                    
                    # Update session_id (overwrites any existing session)
                    cursor.execute("UPDATE users SET session_id = %s WHERE user_id = %s", (session_id, result[0]))
                    connection.commit()
                    
                    print(f"  ✓ Logged in as Student (previous session cleared)\n")
                    response = make_response(redirect(url_for('student.studash')))
                    response.set_cookie('session_id', session_id, max_age=86400)
                    return response
            
            # If we reach here, login failed
            print(f"  ✗ Login failed - invalid credentials\n")
            flash("Invalid username or password", "error")
            return redirect(url_for('auth.unified_login'))
            
        except mysql.connector.Error as err:
            print(f"  ✗ Database error: {err}\n")
            flash(f"System error. Please try again.", "error")
            return redirect(url_for('auth.unified_login'))
            
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def stu_signup():
    """
    Student signup page - DISABLED
    Self-registration is not allowed. Accounts must be created by administrators.
    """
    flash("Self-registration is not allowed. Please contact an administrator to create your account.", "error")
    return redirect(url_for('auth.unified_login'))


@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    user_id = session.get('user_id')
    
    if user_id:
        # Clear session_id in database
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET session_id = NULL WHERE user_id = %s", (user_id,))
            connection.commit()
        except mysql.connector.Error:
            pass
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
    
    # Clear all session data
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('auth.unified_login'))


def verify_session(user_id, session_id):
    """Verify if session is valid"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("SELECT session_id FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0] == session_id:
            return True
        return False
        
    except mysql.connector.Error:
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
