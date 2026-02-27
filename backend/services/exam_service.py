"""
Exam Service - Business logic for exam operations
"""
from backend.models.exam import Exam
from backend.models.question import Question
import uuid

class ExamService:
    """Service class for exam-related business logic"""
    
    @staticmethod
    def get_teacher_exams(authority_id):
        """Get all exams for a teacher with statistics"""
        try:
            exams = Exam.get_all_by_teacher(authority_id)
            return {
                'success': True,
                'exams': exams,
                'count': len(exams)
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def get_exam_details(exam_id, authority_id):
        """Get detailed exam information including questions"""
        try:
            exam_info = Exam.get_by_id(exam_id, authority_id)
            
            if not exam_info:
                return {
                    'success': False,
                    'message': 'Exam not found'
                }
            
            questions = Exam.get_questions(exam_id, authority_id)
            
            exam_data = {
                **exam_info,
                'questions': questions
            }
            
            return {
                'success': True,
                'exam': exam_data
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def create_exam(authority_id, exam_data, questions_data):
        """Create a new exam with questions"""
        try:
            # Generate unique exam link
            exam_link = str(uuid.uuid4())
            exam_data['exam_link'] = exam_link
            
            # Create exam
            exam_id = Exam.create(authority_id, exam_data)
            
            # Create questions
            for question_data in questions_data:
                question_data['exam_id'] = exam_id
                question_data['authority_id'] = authority_id
                Question.create(exam_id, authority_id, question_data)
            
            return {
                'success': True,
                'exam_id': exam_id,
                'exam_link': exam_link
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def duplicate_exam(exam_id, authority_id):
        """Duplicate an existing exam"""
        try:
            new_exam_link = str(uuid.uuid4())
            new_exam_id = Exam.duplicate(exam_id, authority_id, new_exam_link)
            
            if not new_exam_id:
                return {
                    'success': False,
                    'message': 'Exam not found or unauthorized'
                }
            
            return {
                'success': True,
                'exam_id': new_exam_id,
                'message': 'Exam duplicated successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def delete_exam(exam_id, authority_id):
        """Delete an exam"""
        try:
            deleted = Exam.delete(exam_id, authority_id)
            
            if not deleted:
                return {
                    'success': False,
                    'message': 'Exam not found or unauthorized'
                }
            
            return {
                'success': True,
                'message': 'Exam deleted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    @staticmethod
    def calculate_exam_statistics(exam_id, authority_id):
        """Calculate statistics for an exam"""
        try:
            questions = Question.get_by_exam(exam_id, authority_id)
            
            total_questions = len(questions)
            total_marks = sum(q['marks'] for q in questions)
            objective_count = sum(1 for q in questions if q['exam_type'] == 'objective')
            subjective_count = sum(1 for q in questions if q['exam_type'] == 'subjective')
            
            return {
                'success': True,
                'statistics': {
                    'total_questions': total_questions,
                    'total_marks': total_marks,
                    'objective_count': objective_count,
                    'subjective_count': subjective_count
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
