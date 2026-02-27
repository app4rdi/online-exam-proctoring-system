"""
User Model - Handle user-related database operations
"""
from backend.models.database import get_db_cursor
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """User model for handling user operations"""
    
    @staticmethod
    def authenticate(username, password, role):
        """Authenticate user by username, password and role"""
        with get_db_cursor() as cursor:
            if role == 'student':
                cursor.execute("""
                    SELECT user_id, username, password, email, full_name
                    FROM users 
                    WHERE username = %s AND role = 'student'
                """, (username,))
            elif role == 'teacher':
                cursor.execute("""
                    SELECT authority_id, username, password, email, full_name
                    FROM exam_authority 
                    WHERE username = %s
                """, (username,))
            elif role == 'admin':
                cursor.execute("""
                    SELECT admin_id, username, password
                    FROM admin 
                    WHERE username = %s
                """, (username,))
            else:
                return None
            
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                return user
            elif user and user['password'] == password:  # Fallback for unhashed passwords
                return user
            
            return None
    
    @staticmethod
    def get_by_id(user_id, role):
        """Get user by ID and role"""
        with get_db_cursor() as cursor:
            if role == 'student':
                cursor.execute("""
                    SELECT user_id, username, email, full_name, created_at
                    FROM users 
                    WHERE user_id = %s
                """, (user_id,))
            elif role == 'teacher':
                cursor.execute("""
                    SELECT authority_id, username, email, full_name, created_at
                    FROM exam_authority 
                    WHERE authority_id = %s
                """, (user_id,))
            elif role == 'admin':
                cursor.execute("""
                    SELECT admin_id, username
                    FROM admin 
                    WHERE admin_id = %s
                """, (user_id,))
            else:
                return None
            
            return cursor.fetchone()
    
    @staticmethod
    def create_student(username, password, email, full_name):
        """Create a new student"""
        with get_db_cursor() as cursor:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, password, email, full_name, role, created_at)
                VALUES (%s, %s, %s, %s, 'student', NOW())
            """, (username, hashed_password, email, full_name))
            return cursor.lastrowid
    
    @staticmethod
    def create_teacher(username, password, email, full_name):
        """Create a new teacher"""
        with get_db_cursor() as cursor:
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO exam_authority (username, password, email, full_name, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (username, hashed_password, email, full_name))
            return cursor.lastrowid
    
    @staticmethod
    def update_password(user_id, new_password, role):
        """Update user password"""
        with get_db_cursor() as cursor:
            hashed_password = generate_password_hash(new_password)
            
            if role == 'student':
                cursor.execute("""
                    UPDATE users SET password = %s WHERE user_id = %s
                """, (hashed_password, user_id))
            elif role == 'teacher':
                cursor.execute("""
                    UPDATE exam_authority SET password = %s WHERE authority_id = %s
                """, (hashed_password, user_id))
            elif role == 'admin':
                cursor.execute("""
                    UPDATE admin SET password = %s WHERE admin_id = %s
                """, (hashed_password, user_id))
            
            return cursor.rowcount > 0
