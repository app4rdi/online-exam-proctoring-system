"""
Validators - Input validation functions
"""
import re
from datetime import datetime

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password, min_length=6):
    """Validate password strength"""
    if not password or len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    # Check for at least one letter and one number
    has_letter = re.search(r'[a-zA-Z]', password)
    has_number = re.search(r'\d', password)
    
    if not has_letter:
        return False, "Password must contain at least one letter"
    
    if not has_number:
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

def validate_username(username, min_length=3, max_length=50):
    """Validate username format"""
    if not username:
        return False, "Username is required"
    
    if len(username) < min_length:
        return False, f"Username must be at least {min_length} characters long"
    
    if len(username) > max_length:
        return False, f"Username must not exceed {max_length} characters"
    
    # Only alphanumeric, underscore, and dash allowed
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and dashes"
    
    return True, "Username is valid"

def validate_exam_title(title, min_length=3, max_length=200):
    """Validate exam title"""
    if not title or not title.strip():
        return False, "Exam title is required"
    
    title = title.strip()
    
    if len(title) < min_length:
        return False, f"Exam title must be at least {min_length} characters long"
    
    if len(title) > max_length:
        return False, f"Exam title must not exceed {max_length} characters"
    
    return True, "Exam title is valid"

def validate_exam_duration(duration):
    """Validate exam duration"""
    try:
        duration = int(duration)
        
        if duration <= 0:
            return False, "Duration must be greater than 0"
        
        if duration > 600:  # Max 10 hours
            return False, "Duration cannot exceed 600 minutes (10 hours)"
        
        return True, "Duration is valid"
    except (ValueError, TypeError):
        return False, "Duration must be a valid number"

def validate_date(date_str):
    """Validate date format (YYYY-MM-DD)"""
    if not date_str:
        return False, "Date is required"
    
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True, "Date is valid"
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"

def validate_time(time_str):
    """Validate time format (HH:MM)"""
    if not time_str:
        return False, "Time is required"
    
    try:
        datetime.strptime(time_str, '%H:%M')
        return True, "Time is valid"
    except ValueError:
        return False, "Invalid time format. Use HH:MM"

def validate_marks(marks):
    """Validate question marks"""
    try:
        marks = float(marks)
        
        if marks <= 0:
            return False, "Marks must be greater than 0"
        
        if marks > 100:
            return False, "Marks cannot exceed 100"
        
        return True, "Marks are valid"
    except (ValueError, TypeError):
        return False, "Marks must be a valid number"

def validate_question_text(text, min_length=5):
    """Validate question text"""
    if not text or not text.strip():
        return False, "Question text is required"
    
    text = text.strip()
    
    if len(text) < min_length:
        return False, f"Question text must be at least {min_length} characters long"
    
    return True, "Question text is valid"

def validate_options(options_list, min_options=2, max_options=8):
    """Validate multiple choice options"""
    if not options_list or len(options_list) < min_options:
        return False, f"At least {min_options} options are required"
    
    if len(options_list) > max_options:
        return False, f"Maximum {max_options} options allowed"
    
    # Check for empty options
    for i, option in enumerate(options_list):
        if not option or not option.strip():
            return False, f"Option {i+1} cannot be empty"
    
    # Check for duplicate options
    if len(options_list) != len(set(opt.strip().lower() for opt in options_list)):
        return False, "Options must be unique"
    
    return True, "Options are valid"

def validate_correct_answer(correct_answer, options_count):
    """Validate correct answer for multiple choice"""
    if not correct_answer:
        return False, "Correct answer is required"
    
    try:
        # Convert letter to index (A=0, B=1, etc.)
        index = ord(correct_answer.upper()) - 65
        
        if index < 0 or index >= options_count:
            return False, f"Correct answer must be between A and {chr(65 + options_count - 1)}"
        
        return True, "Correct answer is valid"
    except:
        return False, "Invalid correct answer format"
