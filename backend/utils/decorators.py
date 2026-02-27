"""
Decorators - Custom decorators for routes
"""
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify

def login_required(role=None):
    """Decorator to require login for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('Vui lòng đăng nhập để tiếp tục', 'warning')
                return redirect(url_for('unified_login'))
            
            if role and session.get('role') != role:
                flash('Bạn không có quyền truy cập trang này', 'error')
                return redirect(url_for('unified_login'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_login_required(role=None):
    """Decorator to require login for API routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required'
                }), 401
            
            if role and session.get('role') != role:
                return jsonify({
                    'success': False,
                    'message': 'Unauthorized access'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(**validators):
    """Decorator to validate input data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            
            data = request.get_json() if request.is_json else request.form
            errors = {}
            
            for field, validator_func in validators.items():
                value = data.get(field)
                is_valid, message = validator_func(value)
                
                if not is_valid:
                    errors[field] = message
            
            if errors:
                return jsonify({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': errors
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
