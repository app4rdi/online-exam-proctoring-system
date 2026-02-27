"""
Admin Routes Blueprint
Contains all admin-related routes and functionality
"""
from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify
import mysql.connector
import base64
from config import db_config

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== DASHBOARD ====================

@admin_bp.route('/adash')
def admin_dashboard():
    """Admin Dashboard"""
    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Please log in as admin!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    stats = {}
    recent_complaints = []
    recent_exams = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Get statistics
        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['total_students'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM exam_authority")
        stats['total_teachers'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM exam_info")
        stats['total_exams'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM complaints WHERE status = 'pending'")
        stats['pending_complaints'] = cursor.fetchone()['count']

        # Get pending complaints only (chỉ lấy phản hồi chưa xử lý)
        cursor.execute("""
            SELECT c.complaint_id, c.complaint_text, c.submission_time, c.status,
                   c.user_id, c.authority_id,
                   COALESCE(u.fullname, ea.fullname) as user_name,
                   CASE WHEN c.user_id IS NOT NULL THEN 'Student' ELSE 'Teacher' END as user_type
            FROM complaints c
            LEFT JOIN users u ON c.user_id = u.user_id
            LEFT JOIN exam_authority ea ON c.authority_id = ea.authority_id
            WHERE LOWER(c.status) = 'pending'
            ORDER BY c.submission_time DESC
            LIMIT 20
        """)
        recent_complaints = cursor.fetchall()

        # Get recent exams
        cursor.execute("""
            SELECT ei.exam_id, ei.exam_title, ei.exam_date, ei.exam_time,
                   ea.fullname as teacher_name
            FROM exam_info ei
            JOIN exam_authority ea ON ei.authority_id = ea.authority_id
            ORDER BY ei.created_at DESC
            LIMIT 10
        """)
        recent_exams = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    # Create user object for template
    user = {
        'name': session.get('admin_username', 'Administrator'),
        'role': 'admin',
        'avatar': None  # Admin uses default avatar
    }
    
    return render_template('admin/adash.html', 
                         user=user,
                         stats=stats, 
                         recent_complaints=recent_complaints,
                         recent_exams=recent_exams)


# ==================== DATABASE MANAGEMENT ====================

@admin_bp.route('/database')
def admin_database():
    """Admin Database Management"""
    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Please log in as admin!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    tables_info = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        # Get info for each table
        for table in tables:
            table_name = list(table.values())[0]
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            row_count = cursor.fetchone()['count']
            
            # Get table structure
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            
            tables_info.append({
                'name': table_name,
                'row_count': row_count,
                'columns': columns
            })

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('admin.admin_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('admin_db.html', tables=tables_info)


# ==================== SESSION MANAGEMENT ====================

@admin_bp.route('/clear-all-sessions')
def clear_all_sessions():
    """Clear All Sessions"""
    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Please log in as admin!", "warning")
        return redirect(url_for('auth.unified_login'))

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Clear all sessions from database if you have a sessions table
        cursor.execute("DELETE FROM sessions")
        db.commit()

        flash("All sessions cleared successfully!", "success")

    except mysql.connector.Error as err:
        flash(f"Error clearing sessions: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.admin_dashboard'))


# ==================== COMPLAINT MANAGEMENT ====================

@admin_bp.route('/send_reply', methods=['POST'])
def send_reply():
    """Send Reply to Complaint"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    complaint_id = request.form.get('complaint_id')
    reply_text = request.form.get('reply_text')

    if not complaint_id or not reply_text:
        flash("Invalid data provided.", "error")
        return redirect(url_for('admin.admin_dashboard'))

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("""
            UPDATE complaints 
            SET reply_text = %s, status = 'Resolved' 
            WHERE complaint_id = %s
        """, (reply_text, complaint_id))
        db.commit()

        flash("Đã gửi phản hồi thành công!", "success")

    except mysql.connector.Error as err:
        flash(f"Error sending reply: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.admin_dashboard'))


# ==================== USER MANAGEMENT ====================

@admin_bp.route('/manage-students')
def manage_students():
    """Manage Students - List all students"""
    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Please log in as admin!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    students = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT u.user_id, u.fullname, u.email, u.username, u.contact, 
                   sp.profile_image,
                   COUNT(DISTINCT es.id) as exam_count,
                   COUNT(DISTINCT sr.answer_id) as completed_exams
            FROM users u
            LEFT JOIN student_profiles sp ON u.user_id = sp.id
            LEFT JOIN exam_students es ON u.user_id = es.student_id
            LEFT JOIN student_result sr ON u.user_id = sr.user_id
            GROUP BY u.user_id, u.fullname, u.email, u.username, u.contact, sp.profile_image
            ORDER BY u.user_id DESC
        """)
        students = cursor.fetchall()

        # Convert profile_image to base64 if exists
        for student in students:
            if student['profile_image']:
                student['profile_image_base64'] = base64.b64encode(student['profile_image']).decode('utf-8')
            else:
                student['profile_image_base64'] = None

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    # Create user object for template
    user = {
        'name': session.get('admin_username', 'Administrator'),
        'role': 'admin',
        'avatar': None
    }
    
    return render_template('admin/manage_students.html', user=user, students=students)


@admin_bp.route('/manage-teachers')
def manage_teachers():
    """Manage Teachers - List all teachers"""
    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Please log in as admin!", "warning")
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    teachers = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT ea.authority_id, ea.fullname, ea.email, ea.username, 
                   ea.contact,
                   COUNT(DISTINCT ei.exam_id) as exam_count
            FROM exam_authority ea
            LEFT JOIN exam_info ei ON ea.authority_id = ei.authority_id
            GROUP BY ea.authority_id, ea.fullname, ea.email, ea.username, ea.contact
            ORDER BY ea.authority_id DESC
        """)
        teachers = cursor.fetchall()

        # Set profile_image_base64 to None since column doesn't exist
        for teacher in teachers:
            teacher['profile_image_base64'] = None

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    # Create user object for template
    user = {
        'name': session.get('admin_username', 'Administrator'),
        'role': 'admin',
        'avatar': None
    }
    
    return render_template('admin/manage_teachers.html', user=user, teachers=teachers)


@admin_bp.route('/add-student', methods=['POST'])
def add_student():
    """Add new student"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    from werkzeug.security import generate_password_hash

    fullname = request.form.get('fullname')
    email = request.form.get('email')
    username = request.form.get('username')
    contact = request.form.get('contact')
    password = request.form.get('password')

    if not all([fullname, email, username, password]):
        flash("All fields are required!", "error")
        return redirect(url_for('admin.manage_students'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Check if username or email already exists
        cursor.execute("SELECT user_id FROM users WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            flash("Username or email already exists!", "error")
            return redirect(url_for('admin.manage_students'))

        # Insert user
        cursor.execute("""
            INSERT INTO users (fullname, email, username, contact, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (fullname, email, username, contact, hashed_password))
        
        user_id = cursor.lastrowid

        # Create student profile
        cursor.execute("INSERT INTO student_profiles (id) VALUES (%s)", (user_id,))
        
        db.commit()
        flash(f"Student '{fullname}' created successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_students'))


@admin_bp.route('/add-teacher', methods=['POST'])
def add_teacher():
    """Add new teacher"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    from werkzeug.security import generate_password_hash

    fullname = request.form.get('fullname')
    email = request.form.get('email')
    username = request.form.get('username')
    contact = request.form.get('contact')
    password = request.form.get('password')

    if not all([fullname, email, username, password]):
        flash("All fields are required!", "error")
        return redirect(url_for('admin.manage_teachers'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Check if username or email already exists
        cursor.execute("SELECT authority_id FROM exam_authority WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            flash("Username or email already exists!", "error")
            return redirect(url_for('admin.manage_teachers'))

        # Insert teacher
        cursor.execute("""
            INSERT INTO exam_authority (fullname, email, username, contact, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (fullname, email, username, contact, hashed_password))
        
        db.commit()
        flash(f"Teacher '{fullname}' created successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_teachers'))


@admin_bp.route('/edit-student/<int:user_id>', methods=['POST'])
def edit_student(user_id):
    """Edit student information"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    fullname = request.form.get('fullname')
    email = request.form.get('email')
    contact = request.form.get('contact')

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("""
            UPDATE users 
            SET fullname = %s, email = %s, contact = %s
            WHERE user_id = %s
        """, (fullname, email, contact, user_id))
        
        db.commit()
        flash("Student updated successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_students'))


@admin_bp.route('/edit-teacher/<int:authority_id>', methods=['POST'])
def edit_teacher(authority_id):
    """Edit teacher information"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    fullname = request.form.get('fullname')
    email = request.form.get('email')
    contact = request.form.get('contact')

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute("""
            UPDATE exam_authority 
            SET fullname = %s, email = %s, contact = %s
            WHERE authority_id = %s
        """, (fullname, email, contact, authority_id))
        
        db.commit()
        flash("Teacher updated successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_teachers'))


@admin_bp.route('/delete-student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    """Delete student"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Delete related records first (foreign key constraints)
        cursor.execute("DELETE FROM student_profiles WHERE id = %s", (user_id,))
        cursor.execute("DELETE FROM exam_assignments WHERE student_id = %s", (user_id,))
        cursor.execute("DELETE FROM answers WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM complaints WHERE user_id = %s", (user_id,))
        
        # Delete student
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        
        db.commit()
        flash("Student deleted successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_students'))


@admin_bp.route('/delete-teacher/<int:authority_id>', methods=['POST'])
def delete_teacher(authority_id):
    """Delete teacher"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        # Check if teacher has exams
        cursor.execute("SELECT COUNT(*) as count FROM exam_info WHERE authority_id = %s", (authority_id,))
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            flash("Cannot delete teacher with existing exams. Please delete exams first.", "error")
            return redirect(url_for('admin.manage_teachers'))

        # Delete teacher
        cursor.execute("DELETE FROM exam_authority WHERE authority_id = %s", (authority_id,))
        
        db.commit()
        flash("Teacher deleted successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for('admin.manage_teachers'))


@admin_bp.route('/reset-password/<string:user_type>/<int:user_id>', methods=['POST'])
def reset_password(user_type, user_id):
    """Reset user password"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    from werkzeug.security import generate_password_hash

    new_password = request.form.get('new_password')
    if not new_password:
        flash("Password is required!", "error")
        return redirect(url_for(f'admin.manage_{user_type}s'))

    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

    db = None
    cursor = None
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        if user_type == 'student':
            cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed_password, user_id))
        elif user_type == 'teacher':
            cursor.execute("UPDATE exam_authority SET password = %s WHERE authority_id = %s", (hashed_password, user_id))
        
        db.commit()
        flash("Password reset successfully!", "success")

    except mysql.connector.Error as err:
        if db:
            db.rollback()
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return redirect(url_for(f'admin.manage_{user_type}s'))
