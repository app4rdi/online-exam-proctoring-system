"""
Teacher Routes Blueprint
Contains all teacher-related routes and functionality
"""
from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify, send_file, make_response
import mysql.connector
from werkzeug.security import generate_password_hash
import base64
from datetime import datetime
from uuid import uuid4
from io import BytesIO
import os
import glob
from config import db_config, allowed_file, get_teacher_data

# Create Blueprint
teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')


# ==================== DASHBOARD ====================

@teacher_bp.route('/trdash')
def teacher_dashboard():
    """Teacher Dashboard"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exams = []
    stats = {
        'total_exams': 0,
        'upcoming_exams': 0,
        'total_students': 0,
        'recent_violations': 0
    }

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Fetch all exams created by the teacher
        cursor.execute("""
            SELECT 
                ei.exam_id, ei.exam_title, ei.exam_date, ei.exam_time, 
                ei.exam_link, ei.exam_duration,
                COUNT(DISTINCT eq.question_id) as question_count,
                COUNT(DISTINCT sr.answer_id) as submissions_count
            FROM exam_info ei
            LEFT JOIN exam_questions eq ON ei.exam_id = eq.exam_id
            LEFT JOIN student_result sr ON ei.exam_id = sr.exam_id
            WHERE ei.authority_id = %s
            GROUP BY ei.exam_id
            ORDER BY ei.created_at DESC
        """, (authority_id,))
        exams = cursor.fetchall()

        # Calculate statistics
        stats['total_exams'] = len(exams)

        cursor.execute("""
            SELECT COUNT(*) as count FROM exam_info 
            WHERE authority_id = %s AND exam_date >= CURDATE()
        """, (authority_id,))
        result = cursor.fetchone()
        stats['upcoming_exams'] = result['count'] if result else 0

        cursor.execute("""
            SELECT COUNT(DISTINCT sr.user_id) as count 
            FROM student_result sr
            JOIN exam_info ei ON sr.exam_id = ei.exam_id
            WHERE ei.authority_id = %s
        """, (authority_id,))
        result = cursor.fetchone()
        stats['total_students'] = result['count'] if result else 0

        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM violations v
            JOIN exam_info ei ON v.exam_id = ei.exam_id
            WHERE ei.authority_id = %s 
            AND v.timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (authority_id,))
        result = cursor.fetchone()
        stats['recent_violations'] = result['count'] if result else 0

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/trdash.html', user=user_data.get('user'), stats=stats, exams=exams)


@teacher_bp.route('/exams')
def teacher_exams():
    """Teacher Exams List Page - Full exam management"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exams = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Fetch all exams created by the teacher
        cursor.execute("""
            SELECT 
                ei.exam_id, ei.exam_title, ei.exam_date, ei.exam_time, 
                ei.exam_link, ei.exam_duration,
                COUNT(DISTINCT eq.question_id) as question_count,
                COUNT(DISTINCT sr.answer_id) as submissions_count
            FROM exam_info ei
            LEFT JOIN exam_questions eq ON ei.exam_id = eq.exam_id
            LEFT JOIN student_result sr ON ei.exam_id = sr.exam_id
            WHERE ei.authority_id = %s
            GROUP BY ei.exam_id
            ORDER BY ei.created_at DESC
        """, (authority_id,))
        exams = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/exams.html', user=user_data.get('user'), exams=exams)


# ==================== EXAM MANAGEMENT ====================

@teacher_bp.route('/show/<int:exam_id>')
def show_exam(exam_id):
    """Show Exam Details"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exam = None
    questions = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Fetch exam details
        cursor.execute("""
            SELECT exam_id, exam_title, exam_date, exam_time, exam_duration, exam_link
            FROM exam_info 
            WHERE exam_id = %s AND authority_id = %s
        """, (exam_id, authority_id))
        exam = cursor.fetchone()

        if not exam:
            flash("Exam not found or you don't have permission to view it.", "error")
            return redirect(url_for('teacher.teacher_dashboard'))

        # Fetch questions
        cursor.execute("""
            SELECT question_id, question_text, options, correct_answer, marks, question_image
            FROM exam_questions
            WHERE exam_id = %s
            ORDER BY question_id
        """, (exam_id,))
        questions = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('teacher.teacher_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/show.html', 
                         user=user_data.get('user'),
                         exam=exam, 
                         questions=questions,
                         exam_title=exam['exam_title'])


@teacher_bp.route('/tr_createxm', methods=['GET', 'POST'])
def teacher_createxm():
    """Create New Exam"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    user_data = {'user': None}

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        if request.method == 'POST':
            exam_title = request.form.get('exam-title')
            exam_type = request.form.get('exam-type')
            exam_duration = request.form.get('exam-duration')
            exam_date = request.form.get('exam-date')
            exam_time = request.form.get('exam-time')
            exam_rules = request.form.get('exam-rules')
            
            exam_id = int(uuid4().int & (1 << 31) - 1)

            # Insert exam info with all details
            cursor.execute(
                """INSERT INTO exam_info (exam_id, authority_id, exam_title, exam_duration, exam_date, exam_time, exam_rules)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (exam_id, authority_id, exam_title, exam_duration, exam_date, exam_time, exam_rules)
            )

            if exam_type == 'objective':
                questions = request.form.getlist('questions[]')
                marks = request.form.getlist('marks[]')
                options = request.form.getlist('options[]')
                correct_answers = request.form.getlist('correct_answers[]')
                question_images = request.files.getlist('question-images[]')

                for i, question in enumerate(questions):
                    if not question or not question.strip():
                        continue
                        
                    try:
                        mark = float(marks[i]) if i < len(marks) and marks[i] else 0
                    except (ValueError, IndexError):
                        mark = 0

                    correct_answer = int(correct_answers[i]) if i < len(correct_answers) and correct_answers[i] else None

                    image_data = None
                    if i < len(question_images) and question_images[i] and question_images[i].filename:
                        image_data = question_images[i].read()

                    options_text = options[i] if i < len(options) else None

                    cursor.execute(
                        """INSERT INTO exam_questions 
                        (authority_id, exam_id, exam_title, exam_type, question_text, question_image, marks, options, correct_answer) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (authority_id, exam_id, exam_title, exam_type, question, image_data, mark, 
                         options_text, correct_answer)
                    )

            elif exam_type == 'subjective':
                questions = request.form.getlist('questions[]')
                marks = request.form.getlist('marks[]')
                question_images = request.files.getlist('question-images[]')

                for i, question in enumerate(questions):
                    if not question or not question.strip():
                        continue
                        
                    try:
                        mark = float(marks[i]) if i < len(marks) and marks[i] else 0
                    except (ValueError, IndexError):
                        mark = 0

                    image_data = None
                    if i < len(question_images) and question_images[i] and question_images[i].filename:
                        image_data = question_images[i].read()

                    cursor.execute(
                        """INSERT INTO exam_questions 
                        (authority_id, exam_id, exam_title, exam_type, question_text, question_image, marks) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (authority_id, exam_id, exam_title, exam_type, question, image_data, mark)
                    )
            
            db.commit()
            flash("Tạo đề thi thành công!", "success")
            
            # Check if opened in iframe (modal mode)
            if request.headers.get('Sec-Fetch-Dest') == 'iframe' or request.args.get('modal') == '1':
                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Success</title>
                    <style>
                        body {
                            font-family: 'Inter', sans-serif;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            min-height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .success-message {
                            background: white;
                            padding: 40px;
                            border-radius: 16px;
                            text-align: center;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        }
                        .success-icon {
                            font-size: 64px;
                            color: #10b981;
                            margin-bottom: 20px;
                        }
                        h2 {
                            color: #1f2937;
                            margin-bottom: 10px;
                        }
                        p {
                            color: #6b7280;
                        }
                    </style>
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
                </head>
                <body>
                    <div class="success-message">
                        <div class="success-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <h2>Tạo đề thi thành công!</h2>
                        <p>Đang quay lại dashboard...</p>
                    </div>
                    <script>
                        // Notify parent window to close modal
                        if (window.parent !== window) {
                            window.parent.postMessage('examCreated', '*');
                        }
                        // Fallback: redirect after 2 seconds
                        setTimeout(function() {
                            if (window.parent === window) {
                                window.location.href = '/teacher/trdash';
                            }
                        }, 2000);
                    </script>
                </body>
                </html>
                """
            
            return redirect(url_for('teacher.teacher_dashboard'))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        if db:
            db.rollback()
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/tr_createxm.html', user=user_data.get('user'))


# ==================== RESULTS ====================

@teacher_bp.route('/tr_result')
def teacher_result():
    """Teacher Results Page"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    results_data = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Fetch student results for exams created by this teacher
        cursor.execute("""
            SELECT sa.answer_id, sa.user_id, sa.exam_id, sa.fullname, 
                sa.submitted_at, sa.exam_title, sa.score, sa.status 
            FROM student_result sa
            JOIN exam_info ei ON sa.exam_id = ei.exam_id
            WHERE ei.authority_id = %s
            ORDER BY sa.submitted_at DESC
        """, (authority_id,))
        results_data = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'teacher/tr_result.html',
        user=user_data.get('user'),
        results=results_data
    )


@teacher_bp.route('/student_answers')
def student_answers():
    """View Student's Answers"""
    answer_id = request.args.get('answer_id')
    authority_id = session.get('authority_id')

    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    if not answer_id:
        flash("Invalid answer ID!", "error")
        return redirect(url_for('teacher.teacher_result'))

    db = None
    cursor = None
    answers_data = []
    exam_info = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Get exam info and verify teacher owns this exam
        cursor.execute("""
            SELECT sr.exam_id, sr.exam_title, sr.fullname, sr.submitted_at
            FROM student_result sr
            JOIN exam_info ei ON sr.exam_id = ei.exam_id
            WHERE sr.answer_id = %s AND ei.authority_id = %s
        """, (answer_id, authority_id))
        exam_info = cursor.fetchone()

        if not exam_info:
            flash("You don't have permission to view these answers.", "error")
            return redirect(url_for('teacher.teacher_result'))

        # Get student's answers
        cursor.execute("""
            SELECT sa.question_id, q.question_text, sa.answer, 
                   q.correct_answer, q.marks
            FROM student_answers sa
            JOIN exam_questions q ON sa.question_id = q.question_id
            WHERE sa.answer_id = %s
            ORDER BY sa.question_id
        """, (answer_id,))
        answers_data = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('teacher.teacher_result'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'teacher/student_answers.html',
        user=user_data.get('user'),
        exam_info=exam_info,
        answers=answers_data,
        answer_id=answer_id
    )


# ==================== PROFILE & SETTINGS ====================

@teacher_bp.route('/edit_profile', methods=['GET', 'POST'])
def teacher_edit_profile():
    """Edit Teacher Profile"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        if request.method == 'POST':
            # Update basic info
            if 'fullname' in request.form:
                fullname = request.form.get('fullname')
                email = request.form.get('email')
                contact = request.form.get('contact')
                
                cursor.execute("""
                    UPDATE exam_authority 
                    SET fullname = %s, email = %s, contact = %s
                    WHERE authority_id = %s
                """, (fullname, email, contact, authority_id))
                db.commit()
                flash("Profile updated successfully!", "success")
                return redirect(url_for('teacher.teacher_edit_profile'))
            
            # Upload profile image
            if 'profile_image' in request.files and request.files['profile_image'].filename:
                file = request.files['profile_image']
                if file and allowed_file(file.filename):
                    image_binary = file.read()
                    
                    cursor.execute("""
                        INSERT INTO teacher_profiles (id, profile_image) 
                        VALUES (%s, %s) 
                        ON DUPLICATE KEY UPDATE profile_image = VALUES(profile_image)
                    """, (authority_id, image_binary))
                    db.commit()
                    flash("Profile image uploaded successfully!", "success")
                else:
                    flash("Invalid file type. Please upload an image.", "error")
                return redirect(url_for('teacher.teacher_edit_profile'))
            
            # Remove profile image
            elif 'remove_image' in request.form:
                cursor.execute("UPDATE teacher_profiles SET profile_image = NULL WHERE id = %s", (authority_id,))
                db.commit()
                flash("Profile image removed successfully!", "success")
                return redirect(url_for('teacher.teacher_edit_profile'))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/edit_profile.html',
                         user=user_data.get('user'),
                         teacher_data=user_data.get('user'),
                         profile_image=user_data.get('profile_image'))


@teacher_bp.route('/password', methods=['GET', 'POST'])
def change_password():
    """Change Teacher Password"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        if request.method == 'POST':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash("Passwords do not match", "error")
                return redirect(url_for('teacher.change_password'))

            if len(new_password) < 5 or len(new_password) > 12:
                flash("Password must be between 5 and 12 characters", "error")
                return redirect(url_for('teacher.change_password'))

            hashed_password = generate_password_hash(new_password)

            cursor.execute(
                "UPDATE exam_authority SET password = %s WHERE authority_id = %s",
                (hashed_password, authority_id)
            )
            db.commit()

            flash("Password changed successfully!", "success")
            return redirect(url_for('teacher.change_password'))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/password.html', user=user_data.get('user'))


# ==================== COMPLAINTS ====================

@teacher_bp.route('/tr_complaint')
def teacher_complaint():
    """Teacher Complaints Page"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("User ID not found. Please log in again.", "error")
        return redirect(url_for('auth.unified_login'))
    
    connection = None
    complaints = []

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Retrieve complaints
        cursor.execute("""
            SELECT complaint_text, reply_text, status, submission_time 
            FROM complaints 
            WHERE authority_id = %s 
            ORDER BY complaint_id DESC
        """, (authority_id,))
        complaints = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error retrieving complaints: {err}", "error")

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('teacher/tr_complaint.html', user=user_data.get('user'), complaints=complaints)


# ==================== MONITOR ====================

@teacher_bp.route('/monitor')
@teacher_bp.route('/monitor/<int:exam_id>')
def monitor(exam_id=None):
    """Monitor Page - Real-time Exam Monitoring"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exams = []
    exam_title = None
    violations = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Fetch exams for this teacher
        cursor.execute("""
            SELECT exam_id, exam_title, exam_date, exam_time
            FROM exam_info
            WHERE authority_id = %s
            ORDER BY exam_date DESC, exam_time DESC
        """, (authority_id,))
        exams = cursor.fetchall()
        
        # If exam_id is provided, fetch violations for that exam
        if exam_id:
            # Verify exam belongs to this teacher
            cursor.execute("""
                SELECT exam_title 
                FROM exam_info 
                WHERE exam_id = %s AND authority_id = %s
            """, (exam_id, authority_id))
            exam_info = cursor.fetchone()
            
            if not exam_info:
                flash("Exam not found or access denied", "error")
                return redirect(url_for('teacher.monitor'))
            
            exam_title = exam_info['exam_title']
            
            # Fetch violations for this exam
            cursor.execute("""
                SELECT v.violation_id, v.user_id, v.timestamp, v.violation_type,
                       u.fullname as student_name, u.email
                FROM violations v
                JOIN users u ON v.user_id = u.user_id
                WHERE v.exam_id = %s
                ORDER BY v.timestamp DESC
            """, (exam_id,))
            violations = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('teacher.teacher_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/monitor.html', 
                         user=user_data.get('user'), 
                         exams=exams,
                         exam_id=exam_id,
                         exam_title=exam_title,
                         violations=violations)


# ==================== EXAM DETAILS API ====================

@teacher_bp.route('/exam-details/<int:exam_id>')
def get_exam_details(exam_id):
    """API endpoint to get exam details as JSON for modal display"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Get exam info
        cursor.execute("""
            SELECT exam_title, exam_duration, exam_rules, exam_date, exam_time, exam_link 
            FROM exam_info 
            WHERE authority_id = %s AND exam_id = %s LIMIT 1
        """, (authority_id, exam_id))
        exam_info = cursor.fetchone()

        if not exam_info:
            return jsonify({'success': False, 'message': 'Không tìm thấy đề thi'}), 404

        # Fetch all questions
        cursor.execute("""
            SELECT question_text, question_image, marks, options, exam_type, correct_answer
            FROM exam_questions 
            WHERE authority_id = %s AND exam_id = %s
        """, (authority_id, exam_id))
        questions = cursor.fetchall()

        # Convert binary images to base64
        for q in questions:
            if q['question_image']:
                q['question_image'] = base64.b64encode(q['question_image']).decode('utf-8')
            else:
                q['question_image'] = None
                
            # Parse options string into a list
            if q['options'] and q['options'].strip():
                q['options_list'] = [opt.strip() for opt in q['options'].split('\n') if opt.strip()]
            else:
                q['options_list'] = []

        # Prepare response data
        exam_data = {
            'exam_title': exam_info['exam_title'],
            'exam_duration': exam_info['exam_duration'],
            'exam_rules': exam_info['exam_rules'],
            'exam_date': str(exam_info['exam_date']) if exam_info['exam_date'] else None,
            'exam_time': str(exam_info['exam_time']) if exam_info['exam_time'] else None,
            'exam_link': exam_info['exam_link'],
            'questions': questions
        }

        return jsonify({'success': True, 'exam': exam_data})

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'Database error: {str(err)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# ==================== SUBMIT MARKS ====================

@teacher_bp.route('/submit_marks', methods=['POST'])
def submit_marks():
    """Submit marks for student answers"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    answer_id = request.form.get('answer_id')
    overall_mark = request.form.get('overall-mark')
    overall_status = request.form.get('overall-status')

    if not answer_id or not overall_mark or not overall_status:
        flash("All fields are required.", "error")
        return redirect(url_for('teacher.student_answers', answer_id=answer_id))

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Verify the teacher's authority over this exam
        cursor.execute("""
            SELECT ei.authority_id 
            FROM student_result sa
            JOIN exam_info ei ON sa.exam_id = ei.exam_id
            WHERE sa.answer_id = %s
        """, (answer_id,))
        result = cursor.fetchone()

        if not result or result[0] != authority_id:
            flash("Unauthorized action.", "error")
            return redirect(url_for('teacher.teacher_result'))

        # Update the student's results
        cursor.execute("""
            UPDATE student_result 
            SET score = %s, status = %s 
            WHERE answer_id = %s
        """, (int(overall_mark), overall_status, answer_id))
        db.commit()

        flash("Marks and status updated successfully!", "success")
        return redirect(url_for('teacher.teacher_result'))

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Database error: {err}", "error")
        return redirect(url_for('teacher.student_answers', answer_id=answer_id))
    except ValueError:
        flash("Invalid marks entered.", "error")
        return redirect(url_for('teacher.student_answers', answer_id=answer_id))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# ==================== VIOLATIONS ====================

@teacher_bp.route('/violations/<int:user_id>/<int:exam_id>')
def violations_detail(user_id, exam_id):
    """View Violations for Specific User and Exam"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    violations = []
    student_info = None
    exam_info = None
    user_data = {'user': None}

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Get student info
        cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (user_id,))
        student_info = cursor.fetchone()

        # Get exam info
        cursor.execute("SELECT exam_title FROM exam_info WHERE exam_id = %s", (exam_id,))
        exam_info = cursor.fetchone()

        # Get violations with description
        cursor.execute("""
            SELECT violation_id, violation_type, timestamp, num_faces, description
            FROM violations
            WHERE user_id = %s AND exam_id = %s
            ORDER BY timestamp DESC
        """, (user_id, exam_id))
        violations = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('teacher.teacher_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/violations.html',
                         violations=violations,
                         student_info=student_info,
                         exam_info=exam_info,
                         exam_title=exam_info['exam_title'] if exam_info else None,
                         user=user_data.get('user'))


@teacher_bp.route('/violations')
def violations_list():
    """List All Violations with Statistics"""
    authority_id = session.get('authority_id')
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    violations_summary = []
    stats = {}
    user_data = {'user': None}

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Get violations grouped by student and exam
        cursor.execute("""
            SELECT 
                v.user_id, 
                v.exam_id, 
                u.fullname as student_name,
                ei.exam_title,
                COUNT(*) as total_violations,
                MIN(v.timestamp) as first_violation,
                MAX(v.timestamp) as latest_violation,
                GROUP_CONCAT(DISTINCT v.violation_type) as violation_types
            FROM violations v
            JOIN users u ON v.user_id = u.user_id
            JOIN exam_info ei ON v.exam_id = ei.exam_id
            WHERE ei.authority_id = %s
            GROUP BY v.user_id, v.exam_id, u.fullname, ei.exam_title
            ORDER BY MAX(v.timestamp) DESC
        """, (authority_id,))
        violations_summary = cursor.fetchall()

        # Get overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT v.user_id) as unique_students,
                COUNT(DISTINCT v.exam_id) as exams_with_violations
            FROM violations v
            JOIN exam_info ei ON v.exam_id = ei.exam_id
            WHERE ei.authority_id = %s
        """, (authority_id,))
        stats = cursor.fetchone() or {}

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/violations_list.html', 
                         violations_summary=violations_summary,
                         stats=stats,
                         user=user_data.get('user'))


@teacher_bp.route('/violation-image/<int:violation_id>')
def violation_image(violation_id):
    """Serve violation image from violation_screenshots folder"""
    db = None
    cursor = None
    
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)
        
        # Get violation details
        cursor.execute("""
            SELECT user_id, violation_type, timestamp 
            FROM violations 
            WHERE violation_id = %s
        """, (violation_id,))
        violation = cursor.fetchone()
        
        if not violation:
            return "Violation not found", 404
        
        user_id = violation['user_id']
        violation_type = violation['violation_type']
        timestamp = violation['timestamp']
        
        # Convert violation_type for filename matching
        # Database: 'no_face', 'multiple_faces', 'prohibited_object'
        # Filename: 'no_face', 'multiple_faces', 'object_cell phone'
        
        # Format timestamp to match filename pattern: YYYYMMDD_HHMMSS
        date_str = timestamp.strftime('%Y%m%d')
        time_str = timestamp.strftime('%H%M%S')
        
        # Search for matching image file
        screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'violation_screenshots')
        
        # Try different matching patterns
        patterns = [
            f"student_{user_id}_{violation_type}_{date_str}_{time_str}_*.jpg",
            f"student_{user_id}_*_{date_str}_{time_str}_*.jpg",  # Fallback: match by user and time
            f"student_{user_id}_{violation_type}_*.jpg",  # Fallback: match by user and type
            f"student_{user_id}_*.jpg"  # Last resort: any image for this user
        ]
        
        image_path = None
        for pattern in patterns:
            matches = glob.glob(os.path.join(screenshots_dir, pattern))
            if matches:
                # Get the first match, or closest by timestamp
                image_path = matches[0]
                break
        
        if image_path and os.path.exists(image_path):
            return send_file(image_path, mimetype='image/jpeg')
        else:
            # Return placeholder 404
            return "No image found", 404
            
    except mysql.connector.Error as err:
        print(f"Error fetching violation: {err}")
        return "Database error", 500
    except Exception as e:
        print(f"Error serving image: {e}")
        return "Error", 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# ==================== MANAGE EXAM STUDENTS ====================

@teacher_bp.route('/manage-students/<int:exam_id>')
def manage_exam_students(exam_id):
    """Page to manage students for a specific exam"""
    authority_id = session.get('authority_id')
    print(f"🔍 DEBUG: manage_exam_students called with exam_id={exam_id}, authority_id={authority_id}")
    
    if not authority_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exam_info = None
    assigned_students = []
    all_students = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_teacher_data(authority_id, cursor)

        # Get exam info
        cursor.execute("""
            SELECT exam_id, exam_title, exam_date, exam_time, exam_duration,
                   exam_rules, exam_link
            FROM exam_info
            WHERE exam_id = %s AND authority_id = %s
        """, (exam_id, authority_id))
        exam_info = cursor.fetchone()
        
        print(f"🔍 DEBUG: exam_info query result: {exam_info}")

        if not exam_info:
            print(f"❌ DEBUG: Exam {exam_id} not found or no permission for authority {authority_id}")
            flash("Exam not found or you don't have permission!", "error")
            return redirect(url_for('teacher.teacher_dashboard'))

        # Get students already assigned to this exam
        cursor.execute("""
            SELECT es.id, es.student_id, es.has_taken, es.taken_at, es.assigned_at,
                   u.fullname, u.username, u.email
            FROM exam_students es
            JOIN users u ON es.student_id = u.user_id
            WHERE es.exam_id = %s
            ORDER BY u.fullname
        """, (exam_id,))
        assigned_students = cursor.fetchall()

        # Get all students (not assigned to this exam)
        cursor.execute("""
            SELECT u.user_id, u.fullname, u.username, u.email
            FROM users u
            WHERE u.user_id NOT IN (
                SELECT student_id FROM exam_students WHERE exam_id = %s
            )
            ORDER BY u.fullname
        """, (exam_id,))
        all_students = cursor.fetchall()
        
        print(f"✅ DEBUG: Found {len(assigned_students)} assigned students, {len(all_students)} available students")

        # Count questions
        cursor.execute("""
            SELECT COUNT(*) as question_count
            FROM exam_questions
            WHERE exam_id = %s
        """, (exam_id,))
        question_result = cursor.fetchone()
        exam_info['question_count'] = question_result['question_count'] if question_result else 0

    except mysql.connector.Error as err:
        print(f"❌ Database error in manage_exam_students: {err}")
        flash(f"Database error: {err}", "error")
        return redirect(url_for('teacher.teacher_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('teacher/manage_students.html',
                         exam=exam_info,
                         assigned_students=assigned_students,
                         available_students=all_students,
                         user=user_data.get('user'))


@teacher_bp.route('/api/assign-student', methods=['POST'])
def assign_student_to_exam():
    """API to assign a student to an exam"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    data = request.get_json()
    exam_id = data.get('exam_id')
    student_id = data.get('student_id')

    if not exam_id or not student_id:
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Verify exam belongs to this teacher
        cursor.execute("""
            SELECT exam_id FROM exam_info 
            WHERE exam_id = %s AND authority_id = %s
        """, (exam_id, authority_id))
        
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        # Check if student already assigned
        cursor.execute("""
            SELECT id FROM exam_students 
            WHERE exam_id = %s AND student_id = %s
        """, (exam_id, student_id))
        
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Student already assigned'}), 400

        # Assign student to exam
        cursor.execute("""
            INSERT INTO exam_students (exam_id, student_id, assigned_by)
            VALUES (%s, %s, %s)
        """, (exam_id, student_id, authority_id))
        
        db.commit()

        return jsonify({'success': True, 'message': 'Student assigned successfully'})

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@teacher_bp.route('/api/remove-student', methods=['POST'])
def remove_student_from_exam():
    """API to remove a student from an exam"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    data = request.get_json()
    assignment_id = data.get('assignment_id')

    if not assignment_id:
        return jsonify({'success': False, 'message': 'Missing assignment ID'}), 400

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Verify the assignment belongs to teacher's exam and student hasn't taken it
        cursor.execute("""
            SELECT es.id, es.has_taken
            FROM exam_students es
            JOIN exam_info ei ON es.exam_id = ei.exam_id
            WHERE es.id = %s AND ei.authority_id = %s
        """, (assignment_id, authority_id))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': 'Assignment not found'}), 404

        if result[1] == 1:  # has_taken
            return jsonify({'success': False, 'message': 'Cannot remove: Student has already taken the exam'}), 400

        # Remove assignment
        cursor.execute("""
            DELETE FROM exam_students WHERE id = %s
        """, (assignment_id,))
        
        db.commit()

        return jsonify({'success': True, 'message': 'Student removed successfully'})

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@teacher_bp.route('/api/assign-multiple-students', methods=['POST'])
def assign_multiple_students():
    """API to assign multiple students to an exam at once"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    data = request.get_json()
    exam_id = data.get('exam_id')
    student_ids = data.get('student_ids', [])

    if not exam_id or not student_ids:
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    db = None
    cursor = None
    added_count = 0
    skipped_count = 0

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Verify exam belongs to this teacher
        cursor.execute("""
            SELECT exam_id FROM exam_info 
            WHERE exam_id = %s AND authority_id = %s
        """, (exam_id, authority_id))
        
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        # Assign each student
        for student_id in student_ids:
            # Check if already assigned
            cursor.execute("""
                SELECT id FROM exam_students 
                WHERE exam_id = %s AND student_id = %s
            """, (exam_id, student_id))
            
            if cursor.fetchone():
                skipped_count += 1
                continue

            # Assign student
            cursor.execute("""
                INSERT INTO exam_students (exam_id, student_id, assigned_by)
                VALUES (%s, %s, %s)
            """, (exam_id, student_id, authority_id))
            added_count += 1
        
        db.commit()

        message = f"Added {added_count} student(s)"
        if skipped_count > 0:
            message += f", skipped {skipped_count} (already assigned)"

        return jsonify({'success': True, 'message': message, 'added': added_count})

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@teacher_bp.route('/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    """Delete an exam (only if no submissions)"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Check if exam belongs to this teacher and has no submissions
        cursor.execute("""
            SELECT 
                ei.exam_id,
                COUNT(DISTINCT sr.answer_id) as submissions_count
            FROM exam_info ei
            LEFT JOIN student_result sr ON ei.exam_id = sr.exam_id
            WHERE ei.exam_id = %s AND ei.authority_id = %s
            GROUP BY ei.exam_id
        """, (exam_id, authority_id))
        
        exam = cursor.fetchone()
        
        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found or access denied'}), 404

        if exam['submissions_count'] > 0:
            return jsonify({'success': False, 'message': f'Cannot delete: Exam has {exam["submissions_count"]} submissions'}), 400

        # Delete exam and related data in correct order (child tables first)
        cursor.execute("DELETE FROM violations WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_violations WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_students WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_questions WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_reference_images WHERE exam_id = %s", (exam_id,))
        cursor.execute("DELETE FROM exam_info WHERE exam_id = %s", (exam_id,))
        
        db.commit()

        return jsonify({'success': True, 'message': 'Exam deleted successfully'})

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()
