"""
Proctoring System - Main exam monitoring orchestrator
Combines face detection, object detection, and violation tracking
"""
import cv2
import numpy as np
from datetime import datetime
from collections import deque
import json
import os

from backend.proctoring.detectors import FaceDetector, ObjectDetector
from backend.proctoring.utils.violation_tracker import ViolationTracker
from backend.proctoring.utils.screenshot_manager import ScreenshotManager

class ProctoringSystem:
    """Main proctoring system that coordinates all detection modules"""
    
    def __init__(self, 
                 student_id=None,
                 exam_id=None,
                 face_confidence=0.5,
                 object_confidence=0.3,  # Lowered for better detection
                 violation_threshold=1,  # Trigger alert immediately (was 3)
                 screenshot_dir="violation_screenshots"):
        """
        Initialize proctoring system
        
        Args:
            student_id: ID of student being monitored
            exam_id: ID of exam
            face_confidence: Confidence threshold for face detection
            object_confidence: Confidence threshold for object detection
            violation_threshold: Number of violations before alert
            screenshot_dir: Directory to save violation screenshots
        """
        self.student_id = student_id
        self.exam_id = exam_id
        self.violation_threshold = violation_threshold
        
        # Initialize detectors
        try:
            self.face_detector = FaceDetector(confidence_threshold=face_confidence)
            print("✓ Face detector initialized")
        except Exception as e:
            print(f"⚠ Face detector not available: {e}")
            self.face_detector = None
        
        try:
            self.object_detector = ObjectDetector(confidence_threshold=object_confidence)
            print("✓ Object detector initialized")
        except Exception as e:
            print(f"⚠ Object detector not available: {e}")
            self.object_detector = None
        
        # Initialize utilities - threshold=1 for immediate alerts
        self.violation_tracker = ViolationTracker(threshold=1)
        self.screenshot_manager = ScreenshotManager(screenshot_dir)
        
        # Tracking
        self.face_history = deque(maxlen=30)  # Last 30 frames
        self.start_time = datetime.now()
        
    def process_frame(self, frame):
        """
        Process a single frame for violations
        
        Args:
            frame: Input video frame
            
        Returns:
            Dictionary with detection results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'violations': [],
            'face_count': 0,
            'prohibited_items': [],
            'status': 'ok'
        }
        
        # Face detection
        if self.face_detector:
            try:
                # Use comprehensive face check
                face_results = self.face_detector.comprehensive_face_check(frame)
                
                print(f"\n🔍 Face Detection Results:")
                print(f"  Face count: {face_results['face_count']}")
                print(f"  Status: {face_results.get('status', 'unknown')}")
                print(f"  Violations: {len(face_results.get('violations', []))}")
                print(f"  Warnings: {len(face_results.get('warnings', []))}")
                
                results['face_count'] = face_results['face_count']
                self.face_history.append(face_results['face_count'])
                
                # Store additional face info
                results['face_info'] = {
                    'size_ratio': face_results.get('face_size_ratio', 0),
                    'quality': face_results.get('face_quality', 0),
                    'brightness': face_results.get('brightness', 0),
                    'position': face_results.get('face_position', {})
                }
                
                # Handle critical violations (no face, multiple faces)
                for violation_data in face_results.get('violations', []):
                    violation = self.violation_tracker.record_violation(
                        violation_data['type'],
                        violation_data['message']
                    )
                    if violation['alert']:
                        results['violations'].append(violation)
                        results['status'] = 'alert'
                        self.screenshot_manager.save_violation(
                            frame, violation_data['type'], self.student_id
                        )
                
                # Handle warnings (poor quality, small face, etc.) - send to frontend for display
                for warning_data in face_results.get('warnings', []):
                    # Always add warnings to results for real-time frontend display
                    if 'warnings' not in results:
                        results['warnings'] = []
                    results['warnings'].append(warning_data)
                    
                    # Only log to console every 10 frames to avoid spam
                    if len(self.face_history) % 10 == 0:
                        print(f"⚠️  Face Warning: {warning_data['message']}")
                
            except Exception as e:
                print(f"Face detection error: {e}")
                import traceback
                traceback.print_exc()
        
        # Object detection
        if self.object_detector:
            try:
                has_violation, items = self.object_detector.check_violations(frame)
                results['prohibited_items'] = [item['class'] for item in items]
                
                if has_violation:
                    for item in items:
                        # Create descriptive Vietnamese message
                        item_name = item['class']
                        confidence = item.get('confidence', 0) * 100
                        
                        # Translate common items to Vietnamese
                        item_name_vn = {
                            'cell phone': 'điện thoại',
                            'laptop': 'laptop',
                            'book': 'sách',
                            'keyboard': 'bàn phím',
                            'mouse': 'chuột',
                            'remote': 'điều khiển',
                            'tv': 'màn hình'
                        }.get(item_name, item_name)
                        
                        violation = self.violation_tracker.record_violation(
                            'prohibited_object',
                            f"Phát hiện vật cấm: {item_name_vn} ({confidence:.0f}%)",
                            details=item
                        )
                        if violation['alert']:
                            results['violations'].append(violation)
                            results['status'] = 'alert'
                            self.screenshot_manager.save_violation(
                                frame, f"object_{item['class']}", self.student_id
                            )
                
            except Exception as e:
                print(f"Object detection error: {e}")
        
        return results
    
    def get_statistics(self):
        """Get proctoring statistics"""
        return {
            'total_violations': self.violation_tracker.get_total_count(),
            'violations_by_type': self.violation_tracker.get_counts_by_type(),
            'alerts_triggered': self.violation_tracker.get_alert_count(),
            'session_duration': str(datetime.now() - self.start_time),
            'face_detection_history': list(self.face_history)
        }
    
    def get_violations_report(self):
        """Get detailed violations report"""
        return self.violation_tracker.get_all_violations()
    
    def save_report(self, filepath='proctoring_report.json'):
        """Save proctoring report to file"""
        report = {
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'violations': self.get_violations_report()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filepath
    
    def reset(self):
        """Reset all tracking data"""
        self.violation_tracker.reset()
        self.face_history.clear()
        self.start_time = datetime.now()
