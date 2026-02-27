"""
Authentication Service - Handle user authentication and authorization
"""
from backend.models.user import User
from flask import session

class AuthService:
    """Service class for authentication and authorization"""
    
    @staticmethod
    def login(username, password, role):
        """Authenticate user and create session"""
        try:
            user = User.authenticate(username, password, role)
            
            if not user:
                return {
                    'success': False,
                    'message': 'Invalid username or password'
                }
            
            # Create session
            session['role'] = role
            
            if role == 'student':
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['email'] = user.get('email')
                session['full_name'] = user.get('full_name')
            elif role == 'teacher':
                session['authority_id'] = user['authority_id']
                session['username'] = user['username']
                session['email'] = user.get('email')
                session['full_name'] = user.get('full_name')
            elif role == 'admin':
                session['admin_id'] = user['admin_id']
                session['username'] = user['username']
            
            return {
                'success': True,
                'message': 'Login successful',
                'role': role,
                'user': user
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def logout():
        """Clear user session"""
        try:
            session.clear()
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def is_authenticated(role=None):
        """Check if user is authenticated"""
        if role:
            return session.get('role') == role
        return 'role' in session
    
    @staticmethod
    def get_current_user():
        """Get current logged-in user information"""
        if not AuthService.is_authenticated():
            return None
        
        role = session.get('role')
        
        if role == 'student':
            return {
                'role': role,
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'email': session.get('email'),
                'full_name': session.get('full_name')
            }
        elif role == 'teacher':
            return {
                'role': role,
                'authority_id': session.get('authority_id'),
                'username': session.get('username'),
                'email': session.get('email'),
                'full_name': session.get('full_name')
            }
        elif role == 'admin':
            return {
                'role': role,
                'admin_id': session.get('admin_id'),
                'username': session.get('username')
            }
        
        return None
    
    @staticmethod
    def change_password(user_id, old_password, new_password, role):
        """Change user password"""
        try:
            # Verify old password
            user = User.get_by_id(user_id, role)
            
            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            # Update password
            updated = User.update_password(user_id, new_password, role)
            
            if not updated:
                return {
                    'success': False,
                    'message': 'Failed to update password'
                }
            
            return {
                'success': True,
                'message': 'Password changed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
