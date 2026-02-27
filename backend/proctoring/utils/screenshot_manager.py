"""
Screenshot Manager - Save violation screenshots
"""
import cv2
import os
from datetime import datetime

class ScreenshotManager:
    """Manage saving of violation screenshots"""
    
    def __init__(self, screenshot_dir="violation_screenshots"):
        """
        Initialize screenshot manager
        
        Args:
            screenshot_dir: Directory to save screenshots
        """
        self.screenshot_dir = screenshot_dir
        
        # Create directory if doesn't exist
        os.makedirs(screenshot_dir, exist_ok=True)
        
    def save_violation(self, frame, violation_type, student_id=None):
        """
        Save screenshot of violation
        
        Args:
            frame: Image frame to save
            violation_type: Type of violation
            student_id: Student ID (optional)
            
        Returns:
            Path to saved screenshot
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Build filename
        filename_parts = []
        if student_id:
            filename_parts.append(f"student_{student_id}")
        filename_parts.append(violation_type)
        filename_parts.append(timestamp)
        
        filename = "_".join(filename_parts) + ".jpg"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        # Save image
        cv2.imwrite(filepath, frame)
        
        return filepath
    
    def save_annotated(self, frame, violation_type, student_id=None, annotation_text=None):
        """
        Save annotated screenshot with text
        
        Args:
            frame: Image frame
            violation_type: Type of violation
            student_id: Student ID
            annotation_text: Text to draw on image
            
        Returns:
            Path to saved screenshot
        """
        # Copy frame for annotation
        annotated = frame.copy()
        
        # Add text if provided
        if annotation_text:
            cv2.putText(
                annotated,
                annotation_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
        
        # Add timestamp
        timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated,
            timestamp_text,
            (10, annotated.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        # Save
        return self.save_violation(annotated, violation_type, student_id)
    
    def get_screenshots_for_student(self, student_id):
        """Get all screenshots for a student"""
        prefix = f"student_{student_id}_"
        screenshots = []
        
        for filename in os.listdir(self.screenshot_dir):
            if filename.startswith(prefix):
                filepath = os.path.join(self.screenshot_dir, filename)
                screenshots.append(filepath)
        
        return sorted(screenshots)
    
    def cleanup_old_screenshots(self, days=7):
        """
        Delete screenshots older than specified days
        
        Args:
            days: Number of days to keep
        """
        import time
        
        current_time = time.time()
        seconds_in_day = 86400
        threshold = current_time - (days * seconds_in_day)
        
        deleted_count = 0
        
        for filename in os.listdir(self.screenshot_dir):
            filepath = os.path.join(self.screenshot_dir, filename)
            file_modified = os.path.getmtime(filepath)
            
            if file_modified < threshold:
                os.remove(filepath)
                deleted_count += 1
        
        return deleted_count
