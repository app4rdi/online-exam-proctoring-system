"""
Exam API - RESTful endpoints for exam operations
"""
from flask import Blueprint, request, jsonify, session
from backend.services.exam_service import ExamService
from backend.services.auth_service import AuthService

exam_api = Blueprint('exam_api', __name__, url_prefix='/api/exams')

@exam_api.route('/', methods=['GET'])
def get_exams():
    """Get all exams for logged-in teacher"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    result = ExamService.get_teacher_exams(authority_id)
    
    return jsonify(result), 200 if result['success'] else 400

@exam_api.route('/<int:exam_id>', methods=['GET'])
def get_exam_details(exam_id):
    """Get detailed information about an exam"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    result = ExamService.get_exam_details(exam_id, authority_id)
    
    status_code = 200 if result['success'] else (404 if 'not found' in result.get('message', '').lower() else 400)
    return jsonify(result), status_code

@exam_api.route('/', methods=['POST'])
def create_exam():
    """Create a new exam"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    data = request.get_json()
    
    exam_data = {
        'exam_title': data.get('exam_title'),
        'exam_duration': data.get('exam_duration'),
        'exam_date': data.get('exam_date'),
        'exam_time': data.get('exam_time'),
        'exam_rules': data.get('exam_rules', '')
    }
    
    questions_data = data.get('questions', [])
    
    result = ExamService.create_exam(authority_id, exam_data, questions_data)
    
    return jsonify(result), 201 if result['success'] else 400

@exam_api.route('/<int:exam_id>/duplicate', methods=['POST'])
def duplicate_exam(exam_id):
    """Duplicate an existing exam"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    result = ExamService.duplicate_exam(exam_id, authority_id)
    
    return jsonify(result), 201 if result['success'] else 400

@exam_api.route('/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    """Delete an exam"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    result = ExamService.delete_exam(exam_id, authority_id)
    
    return jsonify(result), 200 if result['success'] else 404

@exam_api.route('/<int:exam_id>/statistics', methods=['GET'])
def get_exam_statistics(exam_id):
    """Get statistics for an exam"""
    if not AuthService.is_authenticated('teacher'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    authority_id = session.get('authority_id')
    result = ExamService.calculate_exam_statistics(exam_id, authority_id)
    
    return jsonify(result), 200 if result['success'] else 400
