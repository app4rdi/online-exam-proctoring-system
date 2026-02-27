"""
Exam Model - Handle exam-related database operations
"""
from backend.models.database import get_db_cursor
import base64

class Exam:
    """Exam model for handling exam operations"""
    
    @staticmethod
    def get_all_by_teacher(authority_id):
        """Get all exams created by a teacher"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ei.exam_id, ei.exam_title, ei.exam_date, ei.exam_time, 
                    ei.exam_link, ei.exam_duration, ei.created_at,
                    COUNT(eq.question_id) as question_count
                FROM exam_info ei
                LEFT JOIN exam_questions eq ON ei.exam_id = eq.exam_id
                WHERE ei.authority_id = %s
                GROUP BY ei.exam_id, ei.exam_title, ei.exam_date, ei.exam_time, 
                         ei.exam_link, ei.exam_duration, ei.created_at
                ORDER BY ei.created_at DESC
            """, (authority_id,))
            return cursor.fetchall()
    
    @staticmethod
    def get_by_id(exam_id, authority_id):
        """Get exam details by ID"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT exam_title, exam_duration, exam_rules, exam_date, 
                       exam_time, exam_link, created_at
                FROM exam_info 
                WHERE authority_id = %s AND exam_id = %s LIMIT 1
            """, (authority_id, exam_id))
            return cursor.fetchone()
    
    @staticmethod
    def get_questions(exam_id, authority_id):
        """Get all questions for an exam"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT question_text, question_image, marks, options, 
                       exam_type, correct_answer
                FROM exam_questions 
                WHERE authority_id = %s AND exam_id = %s
            """, (authority_id, exam_id))
            questions = cursor.fetchall()
            
            # Process questions
            for q in questions:
                if q['question_image']:
                    q['question_image'] = base64.b64encode(q['question_image']).decode('utf-8')
                else:
                    q['question_image'] = None
                    
                if q['options'] and q['options'].strip():
                    q['options_list'] = [opt.strip() for opt in q['options'].split('\n') if opt.strip()]
                else:
                    q['options_list'] = []
            
            return questions
    
    @staticmethod
    def create(authority_id, exam_data):
        """Create a new exam"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO exam_info 
                (authority_id, exam_title, exam_duration, exam_date, exam_time, 
                 exam_rules, exam_link, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                authority_id,
                exam_data['exam_title'],
                exam_data['exam_duration'],
                exam_data['exam_date'],
                exam_data['exam_time'],
                exam_data['exam_rules'],
                exam_data['exam_link']
            ))
            return cursor.lastrowid
    
    @staticmethod
    def delete(exam_id, authority_id):
        """Delete an exam and its questions"""
        with get_db_cursor() as cursor:
            # Delete questions first (foreign key constraint)
            cursor.execute("""
                DELETE FROM exam_questions 
                WHERE exam_id = %s AND authority_id = %s
            """, (exam_id, authority_id))
            
            # Delete exam info
            cursor.execute("""
                DELETE FROM exam_info 
                WHERE exam_id = %s AND authority_id = %s
            """, (exam_id, authority_id))
            
            return cursor.rowcount > 0
    
    @staticmethod
    def duplicate(exam_id, authority_id, new_exam_link):
        """Duplicate an exam with all its questions"""
        with get_db_cursor() as cursor:
            # Get original exam info
            cursor.execute("""
                SELECT exam_title, exam_duration, exam_date, exam_time, exam_rules
                FROM exam_info 
                WHERE exam_id = %s AND authority_id = %s
            """, (exam_id, authority_id))
            exam_info = cursor.fetchone()
            
            if not exam_info:
                return None
            
            # Create new exam
            new_title = f"{exam_info['exam_title']} (Copy)"
            cursor.execute("""
                INSERT INTO exam_info 
                (authority_id, exam_title, exam_duration, exam_date, exam_time, 
                 exam_rules, exam_link, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                authority_id,
                new_title,
                exam_info['exam_duration'],
                exam_info['exam_date'],
                exam_info['exam_time'],
                exam_info['exam_rules'],
                new_exam_link
            ))
            new_exam_id = cursor.lastrowid
            
            # Copy questions
            cursor.execute("""
                INSERT INTO exam_questions 
                (exam_id, authority_id, question_text, question_image, marks, 
                 options, exam_type, correct_answer)
                SELECT %s, authority_id, question_text, question_image, marks, 
                       options, exam_type, correct_answer
                FROM exam_questions
                WHERE exam_id = %s AND authority_id = %s
            """, (new_exam_id, exam_id, authority_id))
            
            return new_exam_id
