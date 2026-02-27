"""
Object Detector - Detect prohibited objects during exam
Uses YOLO for object detection
"""
import cv2
import torch
import numpy as np
from ultralytics import YOLO
import os
from pathlib import Path

class ObjectDetector:
    """Object detection using YOLO"""
    
    # Prohibited items during exam (matching COCO dataset class names)
    PROHIBITED_ITEMS = [
        "cell phone",
        "book", 
        "laptop",
        "keyboard",
        "mouse",
        "remote",
        "tv"  # Sometimes tablets/monitors detected as tv
    ]
    
    def __init__(self, model_path="yolov8n.pt", confidence_threshold=0.5):
        """
        Initialize object detector
        
        Args:
            model_path: Path to YOLO model file
            confidence_threshold: Minimum confidence for detection
        """
        self.confidence_threshold = confidence_threshold
        
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        
        # If model_path is relative, make it absolute from project root
        model_path = Path(model_path)
        if not model_path.is_absolute():
            model_path = project_root / model_path
        
        # Check if model exists
        if not model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {model_path}")
        
        print(f"Loading YOLO model from: {model_path}")
        
        # Detect device (CUDA or CPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Object detector using device: {self.device}")
        
        # Load YOLO model
        try:
            self.model = YOLO(str(model_path))
            if torch.cuda.is_available():
                self.model.to(self.device)
            print(f"✓ YOLO model loaded successfully")
            print(f"✓ Model classes: {len(self.model.names)} classes")
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model: {e}")
    
    def detect(self, frame):
        """
        Detect objects in frame
        
        Args:
            frame: Input image frame
            
        Returns:
            List of detected objects with info
        """
        try:
            results = self.model(frame, conf=self.confidence_threshold, verbose=False)
            
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get class name
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    # Get confidence
                    confidence = float(box.conf[0])
                    
                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    detections.append({
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': (int(x1), int(y1), int(x2), int(y2))
                    })
                    
                    # Debug log for detected objects
                    print(f"  Detected: {class_name} ({confidence:.2f})")
            
            if len(detections) > 0:
                print(f"Total objects detected: {len(detections)}")
            
            return detections
        except Exception as e:
            print(f"Error in object detection: {e}")
            return []
    
    def detect_prohibited_items(self, frame):
        """
        Detect only prohibited items
        
        Args:
            frame: Input image frame
            
        Returns:
            List of prohibited items detected
        """
        all_detections = self.detect(frame)
        
        prohibited = []
        for detection in all_detections:
            if detection['class'] in self.PROHIBITED_ITEMS:
                prohibited.append(detection)
                print(f"⚠️ PROHIBITED ITEM DETECTED: {detection['class']} ({detection['confidence']:.2f})")
        
        if len(prohibited) > 0:
            print(f"Total prohibited items: {len(prohibited)}")
        
        return prohibited
    
    def check_violations(self, frame):
        """
        Check for object-based violations
        
        Args:
            frame: Input image frame
            
        Returns:
            (has_violation, prohibited_items_list)
        """
        prohibited_items = self.detect_prohibited_items(frame)
        has_violation = len(prohibited_items) > 0
        
        return has_violation, prohibited_items
    
    def get_violation_summary(self, frame):
        """
        Get summary of violations
        
        Args:
            frame: Input image frame
            
        Returns:
            Dictionary with violation details
        """
        has_violation, items = self.check_violations(frame)
        
        summary = {
            'has_violation': has_violation,
            'violation_count': len(items),
            'prohibited_items': [item['class'] for item in items],
            'details': items
        }
        
        return summary
    
    def annotate_frame(self, frame, detections=None):
        """
        Draw bounding boxes on frame
        
        Args:
            frame: Input image frame
            detections: List of detections (if None, will detect)
            
        Returns:
            Annotated frame
        """
        if detections is None:
            detections = self.detect_prohibited_items(frame)
        
        annotated = frame.copy()
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            
            # Draw rectangle
            color = (0, 0, 255)  # Red for prohibited items
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(
                annotated, 
                (x1, y1 - label_size[1] - 10), 
                (x1 + label_size[0], y1), 
                color, 
                -1
            )
            cv2.putText(
                annotated, 
                label, 
                (x1, y1 - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (255, 255, 255), 
                2
            )
        
        return annotated
