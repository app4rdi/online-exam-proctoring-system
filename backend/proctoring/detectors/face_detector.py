"""
Face Detector - Detect faces and multiple person violations
Uses OpenCV DNN for face detection
"""
import cv2
import numpy as np
import os

class FaceDetector:
    """Face detection using OpenCV DNN model"""
    
    def __init__(self, face_proto="deploy.prototxt", 
                 face_model="res10_300x300_ssd_iter_140000.caffemodel",
                 confidence_threshold=0.5):
        """
        Initialize face detector
        
        Args:
            face_proto: Path to prototxt file
            face_model: Path to caffemodel file
            confidence_threshold: Minimum confidence for detection
        """
        self.confidence_threshold = confidence_threshold
        
        # Check if model files exist
        if not (os.path.exists(face_proto) and os.path.exists(face_model)):
            raise FileNotFoundError(
                f"Face detection model files not found!\n"
                f"Required: {face_proto} and {face_model}"
            )
        
        # Load OpenCV face detection model
        self.net = cv2.dnn.readNetFromCaffe(face_proto, face_model)
        
    def detect(self, frame):
        """
        Detect faces in frame
        
        Args:
            frame: Input image frame
            
        Returns:
            List of face bounding boxes [(x, y, w, h), ...]
        """
        h, w = frame.shape[:2]
        
        # Prepare blob for DNN
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 
            1.0, 
            (300, 300), 
            (104.0, 177.0, 123.0)
        )
        
        # Forward pass
        self.net.setInput(blob)
        detections = self.net.forward()
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.confidence_threshold:
                # Get bounding box
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x2, y2) = box.astype("int")
                
                # Convert to (x, y, width, height) format
                faces.append((x, y, x2 - x, y2 - y))
        
        return faces
    
    def detect_with_confidence(self, frame):
        """
        Detect faces with confidence scores
        
        Args:
            frame: Input image frame
            
        Returns:
            List of tuples [(x, y, w, h, confidence), ...]
        """
        h, w = frame.shape[:2]
        
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 
            1.0, 
            (300, 300), 
            (104.0, 177.0, 123.0)
        )
        
        self.net.setInput(blob)
        detections = self.net.forward()
        
        faces = []
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.confidence_threshold:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x2, y2) = box.astype("int")
                
                faces.append((x, y, x2 - x, y2 - y, float(confidence)))
        
        return faces
    
    def count_faces(self, frame):
        """
        Count number of faces in frame
        
        Args:
            frame: Input image frame
            
        Returns:
            Number of faces detected
        """
        return len(self.detect(frame))
    
    def check_multiple_persons(self, frame, max_allowed=1):
        """
        Check if there are more persons than allowed
        
        Args:
            frame: Input image frame
            max_allowed: Maximum number of persons allowed
            
        Returns:
            (is_violation, face_count)
        """
        face_count = self.count_faces(frame)
        is_violation = face_count > max_allowed
        
        return is_violation, face_count
    
    def check_no_face(self, frame):
        """
        Check if no face is detected
        
        Args:
            frame: Input image frame
            
        Returns:
            True if no face detected
        """
        return self.count_faces(frame) == 0
    
    def check_face_size(self, frame, min_face_ratio=0.08):
        """
        Check if face is too small (person too far from camera)
        
        Args:
            frame: Input image frame
            min_face_ratio: Minimum face area ratio to frame area (default 8%)
            
        Returns:
            (is_too_small, face_area_ratio, message)
        """
        faces = self.detect(frame)
        
        if len(faces) == 0:
            return True, 0, "Không phát hiện khuôn mặt"
        
        # Get largest face
        frame_area = frame.shape[0] * frame.shape[1]
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        face_area = largest_face[2] * largest_face[3]
        face_ratio = face_area / frame_area
        
        if face_ratio < min_face_ratio:
            return True, face_ratio, f"Khuôn mặt quá nhỏ ({face_ratio*100:.1f}%) - Hãy đến gần camera hơn"
        
        return False, face_ratio, "OK"
    
    def check_face_quality(self, frame):
        """
        Check face image quality (blur detection)
        
        Args:
            frame: Input image frame
            
        Returns:
            (is_poor_quality, blur_score, message)
        """
        faces = self.detect(frame)
        
        if len(faces) == 0:
            return True, 0, "Không phát hiện khuôn mặt"
        
        # Get largest face region
        (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
        
        # Ensure coordinates are within frame bounds
        x = max(0, x)
        y = max(0, y)
        x2 = min(frame.shape[1], x + w)
        y2 = min(frame.shape[0], y + h)
        
        if x2 <= x or y2 <= y:
            return True, 0, "Vùng mặt không hợp lệ"
        
        face_roi = frame[y:y2, x:x2]
        
        # Calculate Laplacian variance (blur metric)
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Threshold for blur (lower = more blurry)
        # Lowered threshold for better detection when camera is covered
        blur_threshold = 100  # Increased from 50 to detect more blur cases
        
        if blur_score < blur_threshold:
            return True, blur_score, f"Hình ảnh mờ ({blur_score:.1f}) - Kiểm tra camera hoặc ánh sáng"
        
        return False, blur_score, "OK"
    
    def check_face_position(self, frame):
        """
        Check if face is properly centered in frame
        
        Args:
            frame: Input image frame
            
        Returns:
            (is_off_center, position_info, message)
        """
        faces = self.detect(frame)
        
        if len(faces) == 0:
            return True, {}, "Không phát hiện khuôn mặt"
        
        # Get frame dimensions
        frame_h, frame_w = frame.shape[:2]
        frame_center_x = frame_w / 2
        frame_center_y = frame_h / 2
        
        # Get largest face
        (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
        
        # Calculate face center
        face_center_x = x + w / 2
        face_center_y = y + h / 2
        
        # Calculate offset from center
        offset_x = abs(face_center_x - frame_center_x) / frame_w
        offset_y = abs(face_center_y - frame_center_y) / frame_h
        
        position_info = {
            'face_x': face_center_x,
            'face_y': face_center_y,
            'offset_x': offset_x,
            'offset_y': offset_y
        }
        
        # Check if face is too off-center (more than 30% offset)
        if offset_x > 0.3:
            return True, position_info, "Hãy đặt mặt vào giữa camera (quá lệch ngang)"
        
        if offset_y > 0.3:
            return True, position_info, "Hãy đặt mặt vào giữa camera (quá lệch dọc)"
        
        # Check if face is at edge of frame
        if x < frame_w * 0.05 or (x + w) > frame_w * 0.95:
            return True, position_info, "Khuôn mặt ở rìa khung hình"
        
        if y < frame_h * 0.05 or (y + h) > frame_h * 0.95:
            return True, position_info, "Khuôn mặt ở rìa khung hình"
        
        return False, position_info, "OK"
    
    def check_brightness(self, frame):
        """
        Check if frame has adequate brightness
        
        Args:
            frame: Input image frame
            
        Returns:
            (is_poor_brightness, brightness_value, message)
        """
        # First check overall frame brightness (useful when camera is covered)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        overall_brightness = np.mean(gray_frame)
        
        # If overall frame is very dark (camera covered), flag immediately
        if overall_brightness < 40:
            return True, overall_brightness, f"Camera bị che hoặc quá tối ({overall_brightness:.0f}/255)"
        
        faces = self.detect(frame)
        
        if len(faces) == 0:
            # If no face detected but frame is dark, likely covered
            if overall_brightness < 80:
                return True, overall_brightness, f"Camera có thể bị che ({overall_brightness:.0f}/255)"
            return True, overall_brightness, "Không phát hiện khuôn mặt"
        
        # Get largest face region
        (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
        
        # Ensure coordinates are within bounds
        x = max(0, x)
        y = max(0, y)
        x2 = min(frame.shape[1], x + w)
        y2 = min(frame.shape[0], y + h)
        
        if x2 <= x or y2 <= y:
            return True, 0, "Vùng mặt không hợp lệ"
        
        face_roi = frame[y:y2, x:x2]
        
        # Convert to grayscale and calculate mean brightness
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        brightness = np.mean(gray)
        
        # Check brightness thresholds
        if brightness < 60:
            return True, brightness, f"Quá tối ({brightness:.0f}/255) - Tăng độ sáng"
        
        if brightness > 220:
            return True, brightness, f"Quá sáng ({brightness:.0f}/255) - Giảm độ sáng"
        
        return False, brightness, "OK"
    
    def comprehensive_face_check(self, frame):
        """
        Perform comprehensive face validation
        
        Args:
            frame: Input image frame
            
        Returns:
            Dictionary with all check results
        """
        results = {
            'face_count': self.count_faces(frame),
            'has_face': False,
            'violations': [],
            'warnings': [],
            'status': 'ok'
        }
        
        # Face quality check - Run BEFORE checking face count for better detection
        is_poor, quality_score, quality_msg = self.check_face_quality(frame)
        results['face_quality'] = quality_score
        
        # Brightness check - Run BEFORE face count check to detect covered camera
        is_dark, brightness, brightness_msg = self.check_brightness(frame)
        results['brightness'] = brightness
        
        # Check if camera might be covered (dark + no face or poor quality)
        if is_dark and brightness < 40:
            print(f"  🚫 Camera appears to be covered (brightness: {brightness:.0f})")
            results['warnings'].append({
                'type': 'camera_covered',
                'severity': 'critical',
                'message': 'Camera bị che - Vui lòng bỏ tay ra!'
            })
            results['status'] = 'critical'
        
        # Basic face count check
        if results['face_count'] == 0:
            print(f"  ❌ No face detected in frame (brightness: {brightness:.0f})")
            results['violations'].append({
                'type': 'no_face',
                'severity': 'critical',
                'message': 'Không phát hiện khuôn mặt trong camera'
            })
            results['status'] = 'critical'
            return results
        
        print(f"  ✓ {results['face_count']} face(s) detected (quality: {quality_score:.1f}, brightness: {brightness:.0f})")
        results['has_face'] = True
        
        if results['face_count'] > 1:
            results['violations'].append({
                'type': 'multiple_faces',
                'severity': 'critical',
                'message': f'Phát hiện {results["face_count"]} người (chỉ được phép 1 người)'
            })
            results['status'] = 'critical'
        
        # Face size check
        is_small, size_ratio, size_msg = self.check_face_size(frame)
        results['face_size_ratio'] = size_ratio
        if is_small and results['face_count'] > 0:
            results['warnings'].append({
                'type': 'face_too_small',
                'severity': 'warning',
                'message': size_msg
            })
            if results['status'] == 'ok':
                results['status'] = 'warning'
        
        # Face quality check
        is_poor, quality_score, quality_msg = self.check_face_quality(frame)
        results['face_quality'] = quality_score
        if is_poor and results['face_count'] > 0:
            print(f"  📷 Face quality issue detected: {quality_msg}")  # Debug log
            results['warnings'].append({
                'type': 'poor_quality',
                'severity': 'warning',
                'message': quality_msg
            })
            if results['status'] == 'ok':
                results['status'] = 'warning'
        
        # Brightness check for face region (if not already flagged)
        if is_dark and results['face_count'] > 0 and brightness >= 40:
            print(f"  💡 Brightness issue detected: {brightness_msg}")
            results['warnings'].append({
                'type': 'poor_brightness',
                'severity': 'warning',
                'message': brightness_msg
            })
            if results['status'] == 'ok':
                results['status'] = 'warning'
        
        # Position check
        is_off, position, position_msg = self.check_face_position(frame)
        results['face_position'] = position
        if is_off and results['face_count'] > 0:
            results['warnings'].append({
                'type': 'face_off_center',
                'severity': 'warning',
                'message': position_msg
            })
            if results['status'] == 'ok':
                results['status'] = 'warning'
        
        return results
