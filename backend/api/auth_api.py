"""
Auth API - Authentication endpoints
"""
from flask import Blueprint, request, jsonify
from backend.services.auth_service import AuthService

auth_api = Blueprint('auth_api', __name__, url_prefix='/api/auth')

@auth_api.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    if not all([username, password, role]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    result = AuthService.login(username, password, role)
    
    return jsonify(result), 200 if result['success'] else 401

@auth_api.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    result = AuthService.logout()
    return jsonify(result), 200

@auth_api.route('/me', methods=['GET'])
def get_current_user():
    """Get current logged-in user information"""
    user = AuthService.get_current_user()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    return jsonify({
        'success': True,
        'user': user
    }), 200

@auth_api.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    if not AuthService.is_authenticated():
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    data = request.get_json()
    current_user = AuthService.get_current_user()
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not all([old_password, new_password]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    role = current_user['role']
    user_id = current_user.get('user_id') or current_user.get('authority_id') or current_user.get('admin_id')
    
    result = AuthService.change_password(user_id, old_password, new_password, role)
    
    return jsonify(result), 200 if result['success'] else 400
