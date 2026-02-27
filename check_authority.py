import mysql.connector

db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='proctor'
)
cursor = db.cursor(dictionary=True)

# Get teacher authority_id from exam_authority table
cursor.execute("SELECT authority_id, username FROM exam_authority WHERE username='teacher1'")
teacher = cursor.fetchone()
print(f"Teacher: {teacher}")

# Get exam authority_id
cursor.execute("SELECT exam_id, exam_title, authority_id FROM exam_info WHERE exam_id=1712541987")
exam = cursor.fetchone()
print(f"Exam: {exam}")

# Check if they match
if teacher and exam:
    if teacher['authority_id'] == exam['authority_id']:
        print("✅ Authority IDs match!")
    else:
        print(f"❌ Authority IDs DON'T match:")
        print(f"   Teacher authority_id: {teacher['authority_id']}")
        print(f"   Exam authority_id: {exam['authority_id']}")
        
    # Show all exams from this teacher's authority
    cursor.execute("SELECT COUNT(*) as count FROM exam_info WHERE authority_id = %s", (teacher['authority_id'],))
    result = cursor.fetchone()
    print(f"\nExams with teacher's authority_id ({teacher['authority_id']}): {result['count']}")
    
    # Show all violations with matching authority
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM violations v
        JOIN exam_info ei ON v.exam_id = ei.exam_id
        WHERE ei.authority_id = %s
    """, (teacher['authority_id'],))
    result = cursor.fetchone()
    print(f"Violations with teacher's authority_id: {result['count']}")
    
    # Show exam 1712541987 details
    cursor.execute("SELECT COUNT(*) as count FROM violations WHERE exam_id=1712541987")
    result = cursor.fetchone()
    print(f"\nViolations for exam 1712541987: {result['count']}")
else:
    if not teacher:
        print("❌ Teacher 'teacher1' not found in exam_authority table")
    if not exam:
        print("❌ Exam 1712541987 not found in exam_info table")

cursor.close()
db.close()
