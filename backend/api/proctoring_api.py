"""
Proctoring API - Real-time monitoring endpoints
"""
from flask import Blueprint, request, jsonify, session
from backend.proctoring.proctoring_system import ProctoringSystem
import cv2
import numpy as np
import base64

proctoring_api = Blueprint('proctoring_api', __name__, url_prefix='/api/proctoring')

# Store active proctoring sessions
active_sessions = {}

@proctoring_api.route('/start-session', methods=['POST'])
def start_session():
    """Start a new proctoring session"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    student_id = session.get('user_id')
    exam_id = data.get('exam_id')
    
    if not exam_id:
        return jsonify({'success': False, 'message': 'Exam ID required'}), 400
    
    # Create new proctoring system
    session_key = f"{student_id}_{exam_id}"
    active_sessions[session_key] = ProctoringSystem(
        student_id=student_id,
        exam_id=exam_id
    )
    
    return jsonify({
        'success': True,
        'message': 'Proctoring session started',
        'session_key': session_key
    }), 200

@proctoring_api.route('/process-frame', methods=['POST'])
def process_frame():
    """Process a video frame for violations"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    student_id = session.get('user_id')
    exam_id = data.get('exam_id')
    frame_data = data.get('frame')  # Base64 encoded image
    
    if not all([exam_id, frame_data]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    session_key = f"{student_id}_{exam_id}"
    
    if session_key not in active_sessions:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    try:
        # Decode frame
        img_data = base64.b64decode(frame_data.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process frame
        proctoring_system = active_sessions[session_key]
        results = proctoring_system.process_frame(frame)
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing frame: {str(e)}'
        }), 500

@proctoring_api.route('/get-statistics', methods=['GET'])
def get_statistics():
    """Get proctoring statistics for current session"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    student_id = session.get('user_id')
    exam_id = request.args.get('exam_id')
    
    if not exam_id:
        return jsonify({'success': False, 'message': 'Exam ID required'}), 400
    
    session_key = f"{student_id}_{exam_id}"
    
    if session_key not in active_sessions:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    proctoring_system = active_sessions[session_key]
    statistics = proctoring_system.get_statistics()
    
    return jsonify({
        'success': True,
        'statistics': statistics
    }), 200

@proctoring_api.route('/get-report', methods=['GET'])
def get_report():
    """Get detailed violations report"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    student_id = session.get('user_id')
    exam_id = request.args.get('exam_id')
    
    if not exam_id:
        return jsonify({'success': False, 'message': 'Exam ID required'}), 400
    
    session_key = f"{student_id}_{exam_id}"
    
    if session_key not in active_sessions:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    proctoring_system = active_sessions[session_key]
    report = proctoring_system.get_violations_report()
    
    return jsonify({
        'success': True,
        'violations': report
    }), 200

@proctoring_api.route('/end-session', methods=['POST'])
def end_session():
    """End proctoring session and save report"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    student_id = session.get('user_id')
    exam_id = data.get('exam_id')
    
    if not exam_id:
        return jsonify({'success': False, 'message': 'Exam ID required'}), 400
    
    session_key = f"{student_id}_{exam_id}"
    
    if session_key not in active_sessions:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    # Save report
    proctoring_system = active_sessions[session_key]
    report_path = proctoring_system.save_report(
        f'proctoring_report_{student_id}_{exam_id}.json'
    )
    
    # Get final statistics
    statistics = proctoring_system.get_statistics()
    
    # Remove from active sessions
    del active_sessions[session_key]
    
    return jsonify({
        'success': True,
        'message': 'Session ended',
        'report_path': report_path,
        'statistics': statistics
    }), 200

@proctoring_api.route('/teacher/monitor/<int:exam_id>', methods=['GET'])
def teacher_monitor(exam_id):
    """Get real-time monitoring data for all students in exam"""
    if 'authority_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Get all active sessions for this exam
    exam_sessions = {}
    for key, proctor in active_sessions.items():
        if proctor.exam_id == exam_id:
            student_id = proctor.student_id
            exam_sessions[student_id] = {
                'statistics': proctor.get_statistics(),
                'recent_violations': proctor.get_violations_report()[-5:]  # Last 5
            }
    
    return jsonify({
        'success': True,
        'exam_id': exam_id,
        'active_students': len(exam_sessions),
        'sessions': exam_sessions
    }), 200
