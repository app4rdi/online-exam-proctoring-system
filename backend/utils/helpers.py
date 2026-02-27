"""
Helper Functions - Common utility functions
"""
import base64
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash

def encode_image(image_binary):
    """Encode binary image data to base64 string"""
    if image_binary:
        return base64.b64encode(image_binary).decode('utf-8')
    return None

def decode_image(image_base64):
    """Decode base64 string to binary image data"""
    if image_base64:
        return base64.b64decode(image_base64)
    return None

def format_datetime(dt, format='%Y-%m-%d %H:%M:%S'):
    """Format datetime object to string"""
    if isinstance(dt, datetime):
        return dt.strftime(format)
    return str(dt) if dt else None

def format_date(date, format='%Y-%m-%d'):
    """Format date object to string"""
    if isinstance(date, datetime):
        return date.strftime(format)
    return str(date) if date else None

def format_time(time, format='%H:%M'):
    """Format time object to string"""
    if time:
        if isinstance(time, str):
            return time
        return time.strftime(format)
    return None

def parse_options(options_string, delimiter='\n'):
    """Parse options string to list"""
    if options_string and options_string.strip():
        return [opt.strip() for opt in options_string.split(delimiter) if opt.strip()]
    return []

def format_options(options_list, delimiter='\n'):
    """Format options list to string"""
    if options_list:
        return delimiter.join(options_list)
    return ''

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import re
    # Remove any characters that aren't alphanumeric, dash, underscore, or dot
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    return filename

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_exam_code(prefix='EXAM'):
    """Generate unique exam code"""
    import random
    import string
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}_{timestamp}_{random_str}"

def calculate_duration_text(minutes):
    """Convert minutes to human-readable duration"""
    if minutes < 60:
        return f"{minutes} phút"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours} giờ"
    
    return f"{hours} giờ {remaining_minutes} phút"

def get_letter_choice(index):
    """Convert index to letter choice (A, B, C, D, ...)"""
    return chr(65 + index)  # 65 is ASCII code for 'A'

def get_choice_index(letter):
    """Convert letter choice to index"""
    return ord(letter.upper()) - 65
