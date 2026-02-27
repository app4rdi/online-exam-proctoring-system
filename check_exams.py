"""
Quick script to check exam data in database
"""
import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'proctor'
}

try:
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor(dictionary=True)
    
    print("=" * 60)
    print("📊 EXAM DATA CHECK")
    print("=" * 60)
    
    # Check all exams
    cursor.execute("SELECT exam_id, exam_title, authority_id FROM exam_info")
    exams = cursor.fetchall()
    
    if exams:
        print(f"\n✅ Found {len(exams)} exam(s) in database:\n")
        for exam in exams:
            print(f"  - Exam ID: {exam['exam_id']}")
            print(f"    Title: {exam['exam_title']}")
            print(f"    Authority ID: {exam['authority_id']}")
            print()
    else:
        print("\n❌ NO EXAMS FOUND in database!")
        print("   You need to create an exam first before assigning students.\n")
    
    # Check teachers
    cursor.execute("SELECT authority_id, fullname FROM exam_authority")
    teachers = cursor.fetchall()
    
    if teachers:
        print(f"👨‍🏫 Found {len(teachers)} teacher(s):\n")
        for teacher in teachers:
            print(f"  - Authority ID: {teacher['authority_id']}")
            print(f"    Name: {teacher['fullname']}")
            print()
    
    # Check students
    cursor.execute("SELECT COUNT(*) as count FROM users")
    student_count = cursor.fetchone()['count']
    print(f"👨‍🎓 Found {student_count} student(s) in database\n")
    
    print("=" * 60)
    print("\n💡 TROUBLESHOOTING:")
    print("   1. Đảm bảo bạn đã tạo exam (vào /teacher/tr_createxm)")
    print("   2. Login bằng teacher account có authority_id tương ứng")
    print("   3. Click nút Students trên exam BẠN đã tạo")
    print("=" * 60)
    
    cursor.close()
    db.close()
    
except mysql.connector.Error as err:
    print(f"\n❌ Database Error: {err}")
    print("\n💡 TIP: Kiểm tra:")
    print("   - MySQL server đang chạy")
    print("   - Database 'proctor' đã tồn tại")
    print("   - Config trong db_config đúng")
