"""
Configuration file for Online Exam Proctoring System
Contains database config and helper functions
"""

import os
import base64

# Database configuration
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'proctor')
}

def allowed_file(filename):
    """Check if file extension is allowed for upload"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_data(user_id, cursor):
    """
    Get common user data (fullname, profile_image) for templates
    Returns dict: {'fullname': str, 'profile_image': str, 'user': dict}
    """
    # Fetch fullname
    cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (user_id,))
    user_info = cursor.fetchone()
    fullname = user_info['fullname'] if user_info else None
    
    # Fetch profile image  
    cursor.execute("SELECT profile_image FROM student_profiles WHERE id = %s", (user_id,))
    profile_result = cursor.fetchone()
    profile_image = None
    if profile_result and profile_result['profile_image']:
        profile_image = base64.b64encode(profile_result['profile_image']).decode('utf-8')
    
    # Create user object for template
    user = {
        'name': fullname or 'Student',
        'role': 'student',
        'avatar': f"data:image/jpeg;base64,{profile_image}" if profile_image else None
    }
    
    return {
        'fullname': fullname,
        'profile_image': profile_image,
        'user': user
    }

def get_teacher_data(authority_id, cursor):
    """Get teacher data for templates"""
    cursor.execute("SELECT fullname FROM exam_authority WHERE authority_id = %s", (authority_id,))
    teacher_info = cursor.fetchone()
    fullname = teacher_info['fullname'] if teacher_info else None
    
    # Fetch profile image
    cursor.execute("SELECT profile_image FROM teacher_profiles WHERE id = %s", (authority_id,))
    profile_result = cursor.fetchone()
    profile_image = None
    if profile_result and profile_result['profile_image']:
        profile_image = base64.b64encode(profile_result['profile_image']).decode('utf-8')
    
    user = {
        'name': fullname or 'Teacher',
        'role': 'teacher',
        'avatar': f"data:image/jpeg;base64,{profile_image}" if profile_image else None
    }
    
    return {
        'fullname': fullname,
        'profile_image': profile_image,
        'user': user
    }
