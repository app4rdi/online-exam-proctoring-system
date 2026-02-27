"""
Exam & API Routes Blueprint
Contains exam-related and API routes
"""
from flask import Blueprint, render_template, request, redirect, flash, url_for, session, jsonify, Response, make_response
import mysql.connector
import json
from datetime import datetime
from config import db_config, get_user_data, get_teacher_data

# Create Blueprints
exam_bp = Blueprint('exam', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ==================== EXAM ROUTES ====================

@exam_bp.route('/exam')
def exam_list():
    """List Available Exams - Only shows exams assigned to the student"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exams = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        user_data = get_user_data(user_id, cursor)

        # Get only exams assigned to this student
        cursor.execute("""
            SELECT e.exam_id, e.exam_title, e.exam_date, e.exam_time, e.exam_duration,
                   es.has_taken, es.taken_at, es.assigned_at
            FROM exam_info e
            INNER JOIN exam_students es ON e.exam_id = es.exam_id
            WHERE es.student_id = %s
            ORDER BY es.assigned_at DESC, e.exam_date DESC, e.exam_time DESC
        """, (user_id,))
        exams = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    return render_template('student/exam_list.html', user=user_data.get('user'), exams=exams)


@exam_bp.route('/questions/<int:exam_id>')
def questions(exam_id):
    """Show Exam Questions - Checks if student is assigned and hasn't taken exam yet"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.unified_login'))

    db = None
    cursor = None
    exam_info = None
    questions = []

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Check if student is assigned to this exam and hasn't taken it
        cursor.execute("""
            SELECT es.has_taken, es.taken_at
            FROM exam_students es
            WHERE es.exam_id = %s AND es.student_id = %s
        """, (exam_id, user_id))
        assignment = cursor.fetchone()

        if not assignment:
            flash("You are not assigned to this exam!", "error")
            return redirect(url_for('student.exam_list'))

        if assignment['has_taken']:
            flash(f"You have already taken this exam on {assignment['taken_at'].strftime('%B %d, %Y at %I:%M %p') if assignment['taken_at'] else 'a previous date'}!", "warning")
            return redirect(url_for('student.exam_list'))

        # Get exam info
        cursor.execute("""
            SELECT exam_id, exam_title, exam_duration
            FROM exam_info
            WHERE exam_id = %s
        """, (exam_id,))
        exam_info = cursor.fetchone()

        if not exam_info:
            flash("Exam not found!", "error")
            return redirect(url_for('student.exam_list'))

        # Get questions
        cursor.execute("""
            SELECT question_id, question_text, options, correct_answer, marks
            FROM exam_questions
            WHERE exam_id = %s
            ORDER BY question_id
        """, (exam_id,))
        questions = cursor.fetchall()

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('student.exam_list'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()

    # Create response with no-cache headers to force browser reload
    response = make_response(render_template(
        'student/questions.html', 
        exam=exam_info, 
        questions=questions,
        exam_id=exam_info['exam_id'],
        exam_title=exam_info['exam_title'],
        exam_duration=exam_info['exam_duration']
    ))
    
    # Force browser to always reload this page (no cache)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@exam_bp.route('/submit_exam', methods=['POST'])
def submit_exam():
    """Submit Exam Answers - Marks exam as taken"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        data = request.get_json()
        exam_id = data.get('exam_id')
        answers = data.get('answers', {})

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        # Check if student is assigned and hasn't taken exam
        cursor.execute("""
            SELECT has_taken FROM exam_students
            WHERE exam_id = %s AND student_id = %s
        """, (exam_id, user_id))
        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({'success': False, 'message': 'You are not assigned to this exam'}), 403

        if assignment['has_taken']:
            return jsonify({'success': False, 'message': 'You have already taken this exam'}), 403

        # Get exam and user info
        cursor.execute("SELECT exam_title FROM exam_info WHERE exam_id = %s", (exam_id,))
        exam = cursor.fetchone()
        
        cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if not exam or not user:
            return jsonify({'success': False, 'message': 'Invalid exam or user'}), 400

        # Calculate score
        total_marks = 0
        marks_obtained = 0

        cursor.execute("""
            SELECT question_id, correct_answer, marks
            FROM exam_questions
            WHERE exam_id = %s
        """, (exam_id,))
        questions = cursor.fetchall()

        # Insert answer record
        cursor.execute("""
            INSERT INTO student_result (user_id, exam_id, exam_title, fullname, submitted_at, status)
            VALUES (%s, %s, %s, %s, NOW(), 'submitted')
        """, (user_id, exam_id, exam['exam_title'], user['fullname']))
        answer_id = cursor.lastrowid

        # Process each question
        for question in questions:
            question_id = question['question_id']
            correct_answer = question['correct_answer']
            marks = question['marks']
            total_marks += marks

            student_answer = answers.get(str(question_id))
            is_correct = (student_answer == correct_answer) if student_answer else False
            marks_earned = marks if is_correct else 0
            marks_obtained += marks_earned

            # Insert student answer
            cursor.execute("""
                INSERT INTO student_answers (answer_id, question_id, student_answer, marks_obtained)
                VALUES (%s, %s, %s, %s)
            """, (answer_id, question_id, student_answer, marks_earned))

        # Update result with scores
        status = 'passed' if (marks_obtained / total_marks * 100) >= 50 else 'failed'
        cursor.execute("""
            UPDATE student_result
            SET marks_obtained = %s, total_marks = %s, score = %s, status = %s
            WHERE answer_id = %s
        """, (marks_obtained, total_marks, f"{marks_obtained}/{total_marks}", status, answer_id))

        # Mark exam as taken in exam_students
        cursor.execute("""
            UPDATE exam_students
            SET has_taken = 1, taken_at = NOW()
            WHERE exam_id = %s AND student_id = %s
        """, (exam_id, user_id))

        db.commit()

        return jsonify({
            'success': True,
            'score': marks_obtained,
            'total': total_marks,
            'percentage': round(marks_obtained / total_marks * 100, 2),
            'answer_id': answer_id
        })

    except Exception as e:
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@exam_bp.route('/exam_link/<unique_id>')
def exam_link(unique_id):
    """Access Exam via Unique Link"""
    db = None
    cursor = None

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT exam_id, exam_title, exam_date, exam_time, exam_duration
            FROM exam_info
            WHERE exam_link = %s
        """, (unique_id,))
        exam = cursor.fetchone()

        if not exam:
            flash("Invalid exam link!", "error")
            return redirect(url_for('auth.unified_login'))

        # Store exam info in session
        session['exam_id'] = exam['exam_id']
        
        return redirect(url_for('exam.questions', exam_id=exam['exam_id']))

    except mysql.connector.Error as err:
        flash(f"Error: {err}", "error")
        return redirect(url_for('auth.unified_login'))
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


# ==================== API ROUTES ====================

@api_bp.route('/exams', methods=['GET'])
def get_exams():
    """API: Get All Exams"""
    authority_id = session.get('authority_id')
    if not authority_id:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT exam_id, exam_title, exam_date, exam_time, exam_duration
            FROM exam_info
            WHERE authority_id = %s
            ORDER BY created_at DESC
        """, (authority_id,))
        exams = cursor.fetchall()

        # Convert datetime objects to strings
        for exam in exams:
            if exam['exam_date']:
                exam['exam_date'] = exam['exam_date'].strftime('%Y-%m-%d')
            if exam['exam_time']:
                exam['exam_time'] = str(exam['exam_time'])

        return jsonify({'success': True, 'exams': exams})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()


@api_bp.route('/submit_complaint', methods=['POST'])
def submit_complaint_api():
    """API: Submit Complaint"""
    user_id = session.get('user_id')
    authority_id = session.get('authority_id')
    
    if not user_id and not authority_id:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    try:
        data = request.get_json()
        complaint_text = data.get('complaint_text')

        if not complaint_text:
            return jsonify({'success': False, 'message': 'Complaint text required'}), 400

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        if user_id:
            cursor.execute("""
                INSERT INTO complaints (user_id, complaint_text, status)
                VALUES (%s, %s, 'pending')
            """, (user_id, complaint_text))
        else:
            cursor.execute("""
                INSERT INTO complaints (authority_id, complaint_text, status)
                VALUES (%s, %s, 'pending')
            """, (authority_id, complaint_text))

        db.commit()

        return jsonify({'success': True, 'message': 'Complaint submitted successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()
