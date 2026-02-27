"""
Online Exam Proctoring System
Main Application File - Modular Architecture

This is the streamlined main app file that imports and registers
all routes from organized Blueprint modules.
"""
from flask import Flask, render_template, request, redirect, flash, jsonify, session, url_for, send_file, Response
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import base64
from io import BytesIO
from uuid import uuid4
import uuid
from datetime import datetime
import cv2
import numpy as np
import logging
import time
import json
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# Load environment variables
load_dotenv()

# Optional AI/ML imports - gracefully handle if not installed
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    print("ℹ️  DeepFace not installed. Face verification features will be limited.")
    DEEPFACE_AVAILABLE = False

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("ℹ️  Ultralytics not installed. Object detection features will be limited.")
    YOLO_AVAILABLE = False

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    print("ℹ️  TensorFlow not installed. Some AI features may be limited.")
    TENSORFLOW_AVAILABLE = False

try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    print("ℹ️  dlib not installed. Face landmark detection may be limited.")
    DLIB_AVAILABLE = False

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    print("ℹ️  face_recognition not installed. Face encoding features will be limited.")
    FACE_RECOGNITION_AVAILABLE = False

try:
    from backend.proctoring.proctoring_system import ProctoringSystem
    EXAM_PROCTOR_AVAILABLE = True
except ImportError:
    print("ℹ️  Proctoring module not found. Object detection features will be limited.")
    EXAM_PROCTOR_AVAILABLE = False


# ==================== APP INITIALIZATION ====================

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

# Database Configuration
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'proctor')
}

print(f"\n📊 Database Configuration:")
print(f"   Host: {db_config['host']}")
print(f"   User: {db_config['user']}")
print(f"   Database: {db_config['database']}")
print(f"   Password: {'(empty)' if not db_config['password'] else '(set)'}")


# ==================== REGISTER BLUEPRINTS ====================

from routes import register_blueprints
register_blueprints(app)


# ==================== HEALTH CHECK (for Docker) ====================

@app.route('/health')
def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        # Test database connection
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        db.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'deepface': DEEPFACE_AVAILABLE,
            'yolo': YOLO_AVAILABLE,
            'tensorflow': TENSORFLOW_AVAILABLE
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


# ==================== TEST ROUTES (Development Only) ====================

@app.route('/test-manage-students')
def test_manage_students_page():
    """Test page for debugging manage students functionality"""
    return render_template('test_manage_students.html')


# ==================== PROCTORING ROUTES ====================
# These remain in main app due to heavy integration with ML libraries

@app.route('/verify_faces', methods=['POST'])
def verify_faces():
    """Face verification endpoint"""
    if not DEEPFACE_AVAILABLE:
        return jsonify({'success': False, 'error': 'Face verification not available'}), 503

    try:
        data = request.get_json()
        img1_base64 = data.get('image1')
        img2_base64 = data.get('image2')

        if not img1_base64 or not img2_base64:
            return jsonify({'success': False, 'error': 'Missing images'}), 400

        # Decode base64 images
        import re
        img1_base64 = re.sub('^data:image/.+;base64,', '', img1_base64)
        img2_base64 = re.sub('^data:image/.+;base64,', '', img2_base64)

        img1_data = base64.b64decode(img1_base64)
        img2_data = base64.b64decode(img2_base64)

        # Convert to numpy arrays
        img1_array = np.frombuffer(img1_data, np.uint8)
        img2_array = np.frombuffer(img2_data, np.uint8)

        img1 = cv2.imdecode(img1_array, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(img2_array, cv2.IMREAD_COLOR)

        # Verify faces using DeepFace
        result = DeepFace.verify(img1, img2, enforce_detection=False)

        return jsonify({
            'success': True,
            'verified': result['verified'],
            'distance': result['distance'],
            'threshold': result['threshold']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/process_frame', methods=['POST'])
def process_frame():
    """Process exam frame for violations"""
    if not EXAM_PROCTOR_AVAILABLE:
        return jsonify({'success': False, 'error': 'Proctoring not available'}), 503

    db = None
    cursor = None
    try:
        data = request.get_json()
        frame_data = data.get('frame')
        exam_id = data.get('exam_id')
        user_id = session.get('user_id')

        if not frame_data or not exam_id or not user_id:
            return jsonify({'success': False, 'error': 'Missing data'}), 400

        # Decode frame
        import re
        frame_data = re.sub('^data:image/.+;base64,', '', frame_data)
        frame_bytes = base64.b64decode(frame_data)
        frame_array = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

        # Initialize proctoring system with user/exam context
        proctor = ProctoringSystem(student_id=user_id, exam_id=exam_id)
        
        # Process frame and get AI detection results
        results = proctor.process_frame(frame)

        # Auto-log critical violations to database
        violations = results.get('violations', [])
        if violations:
            try:
                db = mysql.connector.connect(**db_config)
                cursor = db.cursor()
                
                for violation in violations:
                    if violation.get('alert', False):  # Only log violations that trigger alerts
                        violation_type = violation.get('type', 'unknown')
                        description = violation.get('description', 'AI detected violation')
                        
                        cursor.execute("""
                            INSERT INTO violations (user_id, exam_id, violation_type, timestamp)
                            VALUES (%s, %s, %s, NOW())
                        """, (user_id, exam_id, f"ai_{violation_type}"))
                        
                        print(f"✓ Logged violation to database: {violation_type} for user {user_id}")
                
                db.commit()
            except Exception as log_error:
                logging.error(f"Failed to log violations to database: {str(log_error)}")
            finally:
                if cursor:
                    cursor.close()
                if db and db.is_connected():
                    db.close()

        return jsonify({
            'success': True,
            'violations': violations,
            'face_count': results.get('face_count', 0),
            'prohibited_items': results.get('prohibited_items', []),
            'status': results.get('status', 'ok')
        })

    except Exception as e:
        logging.error(f"Frame processing error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/log_violation', methods=['POST'])
def log_violation():
    """Log proctoring violation"""
    try:
        data = request.get_json()
        user_id = data.get('user_id') or session.get('user_id')
        exam_id = data.get('exam_id')
        violation_type = data.get('violation_type')
        severity = data.get('severity', 'medium')
        description = data.get('description', '')
        frame_data = data.get('frame')

        if not user_id or not exam_id or not violation_type:
            return jsonify({'success': False, 'error': 'Missing required data'}), 400

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Decode and store frame if provided
        screenshot_data = None
        if frame_data:
            import re
            frame_data = re.sub('^data:image/.+;base64,', '', frame_data)
            screenshot_data = base64.b64decode(frame_data)

        cursor.execute("""
            INSERT INTO violations (user_id, exam_id, violation_type, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, exam_id, violation_type))

        db.commit()
        violation_id = cursor.lastrowid

        return jsonify({
            'success': True,
            'violation_id': violation_id
        })

    except Exception as e:
        logging.error(f"Violation logging error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route('/violation_image/<int:violation_id>')
def violation_image(violation_id):
    """Serve violation screenshot"""
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("SELECT screenshot FROM violations WHERE violation_id = %s", (violation_id,))
        result = cursor.fetchone()

        if result and result[0]:
            return send_file(
                BytesIO(result[0]),
                mimetype='image/jpeg',
                as_attachment=False
            )
        else:
            return "Image not found", 404

    except Exception as e:
        return str(e), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# ==================== LEGACY ROUTES (To be migrated) ====================

@app.route('/delete-exam/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    """Delete Exam - Legacy route"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Verify ownership
        cursor.execute("SELECT authority_id FROM exam_info WHERE exam_id = %s", (exam_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != authority_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Delete exam and related data
        cursor.execute("DELETE FROM exam_questions WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_info WHERE exam_id = %s", (exam_id,))
        db.commit()

        return jsonify({'success': True, 'message': 'Exam deleted successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route('/duplicate-exam/<int:exam_id>', methods=['POST'])
def duplicate_exam(exam_id):
    """Duplicate Exam - Legacy route"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Get original exam
        cursor.execute("""
            SELECT exam_title, exam_date, exam_time, exam_duration
            FROM exam_info WHERE exam_id = %s AND authority_id = %s
        """, (exam_id, authority_id))
        exam = cursor.fetchone()

        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        # Create duplicate
        new_title = f"{exam['exam_title']} (Copy)"
        new_link = str(uuid4())

        cursor.execute("""
            INSERT INTO exam_info (authority_id, exam_title, exam_date, exam_time, exam_duration, exam_link)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (authority_id, new_title, exam['exam_date'], exam['exam_time'], exam['exam_duration'], new_link))
        
        new_exam_id = cursor.lastrowid

        # Duplicate questions
        cursor.execute("SELECT * FROM exam_questions WHERE exam_id = %s", (exam_id,))
        questions = cursor.fetchall()

        for q in questions:
            cursor.execute("""
                INSERT INTO exam_questions (exam_id, authority_id, exam_title, exam_type, question_text, options, correct_answer, marks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (new_exam_id, authority_id, new_title, q.get('exam_type', 'objective'), q['question_text'], q.get('options'), q.get('correct_answer'), q.get('marks', 0)))

        db.commit()

        return jsonify({'success': True, 'message': 'Exam duplicated successfully', 'new_exam_id': new_exam_id})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route('/send_reply', methods=['POST'])
def send_reply():
    """Send reply to complaint - Legacy route"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    complaint_id = request.form.get('complaint_id')
    reply_text = request.form.get('reply_text')

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("""
            UPDATE complaints 
            SET reply_text = %s, status = 'resolved' 
            WHERE complaint_id = %s
        """, (reply_text, complaint_id))
        db.commit()

        flash("Reply sent successfully!", "success")
        return redirect(url_for('admin.admin_dashboard'))

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('admin.admin_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@app.route('/submit_teacher_complaint', methods=['POST'])
def submit_teacher_complaint():
    """Submit teacher complaint - Legacy route"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("User ID not found. Please log in again.", "error")
        return redirect(url_for('auth.unified_login'))

    complaint_text = request.form.get('complaint_text')

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO complaints (authority_id, complaint_text, status) 
            VALUES (%s, %s, 'pending')
        """, (authority_id, complaint_text))
        db.commit()

        flash("Complaint submitted successfully!", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('teacher.teacher_complaint'))


# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("\n" + "=" * 60)
    print(" 🎓 Online Exam Proctoring System - Modular Architecture")
    print("=" * 60)
    print(f" Database: {db_config['database']}@{db_config['host']}")
    print(f" Server: http://localhost:{port}")
    print(f" Status: Running...")
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=port, debug=True)
