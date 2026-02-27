"""
Question Model - Handle question-related database operations
"""
from backend.models.database import get_db_cursor

class Question:
    """Question model for handling question operations"""
    
    @staticmethod
    def create(exam_id, authority_id, question_data):
        """Create a new question"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO exam_questions 
                (exam_id, authority_id, question_text, question_image, marks, 
                 options, exam_type, correct_answer)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                exam_id,
                authority_id,
                question_data['question_text'],
                question_data.get('question_image'),
                question_data['marks'],
                question_data.get('options'),
                question_data['exam_type'],
                question_data.get('correct_answer')
            ))
            return cursor.lastrowid
    
    @staticmethod
    def get_by_exam(exam_id, authority_id):
        """Get all questions for an exam"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT question_id, question_text, question_image, marks, 
                       options, exam_type, correct_answer
                FROM exam_questions 
                WHERE exam_id = %s AND authority_id = %s
                ORDER BY question_id
            """, (exam_id, authority_id))
            return cursor.fetchall()
    
    @staticmethod
    def delete(question_id, authority_id):
        """Delete a question"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                DELETE FROM exam_questions 
                WHERE question_id = %s AND authority_id = %s
            """, (question_id, authority_id))
            return cursor.rowcount > 0
    
    @staticmethod
    def update(question_id, authority_id, question_data):
        """Update a question"""
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE exam_questions 
                SET question_text = %s, question_image = %s, marks = %s, 
                    options = %s, exam_type = %s, correct_answer = %s
                WHERE question_id = %s AND authority_id = %s
            """, (
                question_data['question_text'],
                question_data.get('question_image'),
                question_data['marks'],
                question_data.get('options'),
                question_data['exam_type'],
                question_data.get('correct_answer'),
                question_id,
                authority_id
            ))
            return cursor.rowcount > 0
