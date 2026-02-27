"""
Student Routes Blueprint
Contains all student-related routes and functionality
"""
from flask import Blueprint, render_template, request, redirect, flash, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash
import base64
import os
from config import db_config, allowed_file, get_user_data

# Create Blueprint
student_bp = Blueprint('student', __name__, url_prefix='/student')


# ==================== DASHBOARD ROUTES ====================

@student_bp.route('/studash')
def studash():
    """Student Dashboard"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    profile_image = None
    fullname = None
    username = session.get('username')

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Fetch full name from users table
        cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (user_id,))
        user_info = cursor.fetchone()
        if user_info:
            fullname = user_info[0]

        # Fetch profile image
        cursor.execute("SELECT profile_image FROM student_profiles WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            profile_image = base64.b64encode(result[0]).decode('utf-8')
        
        # Get exam statistics
        try:
            cursor.execute("SELECT COUNT(*) FROM exam_info")
            available_exams = cursor.fetchone()[0] or 0
        except:
            available_exams = 0
        
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT exam_id) FROM student_result 
                WHERE user_id = %s
            """, (user_id,))
            completed_exams = cursor.fetchone()[0] or 0
        except:
            completed_exams = 0
        
        pending_exams = max(0, available_exams - completed_exams)
        
        try:
            cursor.execute("""
                SELECT AVG(score) as avg_score
                FROM student_result 
                WHERE user_id = %s
            """, (user_id,))
            avg_result = cursor.fetchone()
            average_score = round(avg_result[0]) if avg_result and avg_result[0] else 0
        except:
            average_score = 0

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()
    
    # Prepare data for template
    user = {
        'name': fullname or username or 'Student',
        'role': 'student',
        'avatar': f"data:image/png;base64,{profile_image}" if profile_image else None
    }
    
    stats = {
        'available_exams': available_exams,
        'completed_exams': completed_exams,
        'pending_exams': pending_exams,
        'average_score': average_score
    }

    return render_template('student/studash.html', user=user, stats=stats)


@student_bp.route('/stu_result')
def stu_result():
    """Student Results Page"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    results_data = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        cursor.execute("""
            SELECT sa.answer_id, sa.exam_id, sa.exam_title, sa.submitted_at, 
                   sa.score, sa.status
            FROM student_result sa
            WHERE sa.user_id = %s
            ORDER BY sa.submitted_at DESC
        """, (user_id,))
        results_data = cursor.fetchall()

        for result in results_data:
            if result['score'] is None:
                result['score'] = "Not graded yet"

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'student/stu_result.html',
        user=user_data.get('user'),
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname'),
        results=results_data
    )


# ==================== PROFILE ROUTES ====================

@student_bp.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit Student Profile"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        if request.method == 'POST':
            # Update basic info
            if 'fullname' in request.form:
                fullname = request.form.get('fullname')
                email = request.form.get('email')
                contact = request.form.get('contact')
                
                cursor.execute("""
                    UPDATE users 
                    SET fullname = %s, email = %s, contact = %s
                    WHERE user_id = %s
                """, (fullname, email, contact, user_id))
                db.commit()
                flash("Profile updated successfully!", "success")
                return redirect(url_for('student.edit_profile'))
            
            # Upload profile image
            if 'profile_image' in request.files and request.files['profile_image'].filename:
                file = request.files['profile_image']
                if file and allowed_file(file.filename):
                    image_binary = file.read()
                    
                    cursor.execute("""
                        INSERT INTO student_profiles (id, profile_image) 
                        VALUES (%s, %s) 
                        ON DUPLICATE KEY UPDATE profile_image = VALUES(profile_image)
                    """, (user_id, image_binary))
                    db.commit()
                    flash("Profile image uploaded successfully!", "success")
                else:
                    flash("Invalid file type. Please upload an image (png, jpg, jpeg, gif).", "error")
                return redirect(url_for('student.edit_profile'))
            
            # Remove profile image
            elif 'remove_image' in request.form:
                cursor.execute("UPDATE student_profiles SET profile_image = NULL WHERE id = %s", (user_id,))
                db.commit()
                flash("Profile image removed successfully!", "success")
                return redirect(url_for('student.edit_profile'))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'student/edit_profile.html',
        user=user_data.get('user'),
        user_data=user_data.get('user'),
        profile_image=user_data.get('profile_image')
    )


@student_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    """Change Password"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        if request.method == 'POST':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash("Passwords do not match", "error")
                return redirect(url_for('student.change_password'))

            if len(new_password) < 5 or len(new_password) > 12:
                flash("Password must be between 5 and 12 characters", "error")
                return redirect(url_for('student.change_password'))

            hashed_password = generate_password_hash(new_password)

            cursor.execute(
                "UPDATE users SET password = %s WHERE user_id = %s",
                (hashed_password, user_id)
            )
            db.commit()

            flash("Password changed successfully!", "success")
            return redirect(url_for('student.change_password'))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'student/password.html',
        user=user_data.get('user'),
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname')
    )


# ==================== COMPLAINT ROUTES ====================

@student_bp.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    """Submit Complaint"""
    user_id = session.get('user_id')
    if not user_id:
        flash("User ID not found. Please log in again.", "error")
        return redirect(url_for('auth.unified_login'))

    complaint_text = request.form.get('complaint_text')

    if not complaint_text:
        flash("Complaint text is required.", "error")
        return redirect(url_for('student.stu_complaint'))

    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute("INSERT INTO complaints (user_id, complaint_text, status) VALUES (%s, %s, %s)", 
                      (user_id, complaint_text, 'pending'))
        connection.commit()

        flash("Complaint submitted successfully!", "success")

    except mysql.connector.Error as err:
        flash(f"Error submitting complaint: {err}", "error")

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('student.stu_complaint'))


@student_bp.route('/stu_complaint')
def stu_complaint():
    """Student Complaints Page"""
    user_id = session.get('user_id')
    if not user_id:
        flash("User ID not found. Please log in again.", "error")
        return redirect(url_for('auth.unified_login'))

    connection = None
    complaints = []

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        cursor.execute("""
            SELECT complaint_text, reply_text, status, submission_time
            FROM complaints
            WHERE user_id = %s
            ORDER BY complaint_id DESC
        """, (user_id,))
        complaints = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error retrieving complaints: {err}", "error")

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return render_template(
        'student/stu_complaint.html',
        user=user_data.get('user'),
        complaints=complaints,
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname')
    )


# ==================== EXAM ROUTES ====================

@student_bp.route('/exam_list')
def exam_list():
    """List all exams assigned to the student"""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exams = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        # Fetch all exams assigned to this student
        cursor.execute("""
            SELECT 
                e.exam_id,
                e.exam_title,
                e.exam_date,
                e.exam_time,
                e.exam_duration,
                es.has_taken,
                es.assigned_at,
                es.taken_at
            FROM exam_students es
            JOIN exam_info e ON es.exam_id = e.exam_id
            WHERE es.student_id = %s
            ORDER BY 
                CASE WHEN es.has_taken = 0 THEN 0 ELSE 1 END,
                e.exam_date DESC,
                e.exam_time DESC
        """, (user_id,))
        exams = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error loading exams: {err}", "error")
        print(f"Database error: {err}")

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'student/exam_list.html',
        user=user_data.get('user'),
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname'),
        exams=exams
    )


@student_bp.route('/exam_answers')
def exam_answers():
    """View Student's Exam Answers"""
    answer_id = request.args.get('answer_id')
    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in first!", "warning")
        return redirect(url_for('auth.unified_login'))

    if not answer_id:
        flash("Invalid answer ID!", "error")
        return redirect(url_for('student.stu_result'))

    db = None
    cursor = None
    answers_data = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

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
        return redirect(url_for('student.stu_result'))

    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template(
        'student/exam_answers.html',
        user=user_data.get('user'),
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname'),
        answers=answers_data,
        answer_id=answer_id
    )


# ==================== VIOLATIONS ROUTES ====================

@student_bp.route('/violations/<user_id>/<exam_id>')
def violations_detail(user_id, exam_id):
    """View violations for student's exam (student can only view their own)"""
    session_user_id = session.get('user_id')
    if not session_user_id:
        return redirect(url_for('auth.unified_login'))
    
    # Security check: student can only view their own violations
    if str(session_user_id) != str(user_id):
        flash('You can only view your own violations', 'error')
        return redirect(url_for('student.stu_result'))
    
    db = None
    cursor = None
    violations = []
    exam_name = None
    student_name = None
    
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)
        
        # Get user data for topbar
        user_data = get_user_data(session_user_id, cursor)
        
        # Get exam name
        cursor.execute("SELECT exam_name FROM exams WHERE exam_id = %s", (exam_id,))
        exam = cursor.fetchone()
        if exam:
            exam_name = exam['exam_name']
        
        # Get student name
        cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            student_name = user['fullname']
        
        # Get violations
        cursor.execute("""
            SELECT v.*, e.exam_name, u.fullname as student_name
            FROM violations v
            JOIN exams e ON v.exam_id = e.exam_id
            JOIN users u ON v.user_id = u.user_id
            WHERE v.user_id = %s AND v.exam_id = %s
            ORDER BY v.timestamp DESC
        """, (user_id, exam_id))
        violations = cursor.fetchall()
        
    except mysql.connector.Error as e:
        flash(f'Database error: {e}', 'error')
        print(f"Error fetching violations: {e}")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()
    
    return render_template(
        'teacher/violations.html',  # Reuse teacher template
        user=user_data.get('user'),
        profile_image=user_data.get('profile_image'),
        fullname=user_data.get('fullname'),
        violations=violations,
        exam_name=exam_name,
        student_name=student_name,
        is_student_view=True  # Flag to customize template for student
    )


# ==================== STATIC PAGES ====================

@student_bp.route('/about')
def about():
    """About Page"""
    return render_template('student/about.html')


@student_bp.route('/contact')
def contact():
    """Contact Page"""
    return render_template('student/contact.html')


@student_bp.route('/faq')
def faq():
    """FAQ Page"""
    return render_template('faq.html')
