"""
Routes package for Online Exam Proctoring System
This package contains all route blueprints organized by user role
"""

from flask import Blueprint

# Import blueprints
from .auth_routes import auth_bp
from .student_routes import student_bp
from .teacher_routes import teacher_bp
from .admin_routes import admin_bp
from .exam_routes import exam_bp, api_bp

def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(api_bp)
    
    print("\n✅ Blueprints registered successfully!")
    print("   - auth_bp: Authentication")
    print("   - student_bp: /student/*")
    print("   - teacher_bp: /teacher/*")
    print("   - admin_bp: /admin/*")
    print("   - exam_bp: Exam routes")
    print("   - api_bp: /api/*\n")

