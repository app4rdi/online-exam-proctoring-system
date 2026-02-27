"""
Violation Tracker - Track and count violations
"""
from datetime import datetime
from collections import defaultdict

class ViolationTracker:
    """Track violations and trigger alerts"""
    
    def __init__(self, threshold=3, cooldown_seconds=10):
        """
        Initialize violation tracker
        
        Args:
            threshold: Number of violations before alert
            cooldown_seconds: Seconds between alerts for same violation type
        """
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        
        # Tracking
        self.violations = []
        self.violation_counts = defaultdict(int)
        self.last_alert_time = defaultdict(lambda: None)
        self.alert_count = 0
        
    def record_violation(self, violation_type, message, details=None):
        """
        Record a violation
        
        Args:
            violation_type: Type of violation (no_face, multiple_faces, etc.)
            message: Human-readable message
            details: Additional details (optional)
            
        Returns:
            Dictionary with violation info and alert status
        """
        timestamp = datetime.now()
        
        # Increment count
        self.violation_counts[violation_type] += 1
        
        # Check if should trigger alert
        should_alert = self._should_trigger_alert(violation_type, timestamp)
        
        # Record violation
        violation = {
            'type': violation_type,
            'description': message,  # Changed from 'message' to 'description' for frontend compatibility
            'message': message,      # Keep for backward compatibility
            'timestamp': timestamp.isoformat(),
            'count': self.violation_counts[violation_type],
            'alert': should_alert,
            'details': details
        }
        
        self.violations.append(violation)
        
        if should_alert:
            self.alert_count += 1
            self.last_alert_time[violation_type] = timestamp
        
        return violation
    
    def _should_trigger_alert(self, violation_type, current_time):
        """Check if should trigger alert for this violation"""
        count = self.violation_counts[violation_type]
        
        # Check threshold
        if count < self.threshold:
            return False
        
        # Check cooldown
        last_alert = self.last_alert_time[violation_type]
        if last_alert:
            seconds_since_alert = (current_time - last_alert).total_seconds()
            if seconds_since_alert < self.cooldown_seconds:
                return False
        
        return True
    
    def get_total_count(self):
        """Get total number of violations"""
        return len(self.violations)
    
    def get_counts_by_type(self):
        """Get violation counts by type"""
        return dict(self.violation_counts)
    
    def get_alert_count(self):
        """Get number of alerts triggered"""
        return self.alert_count
    
    def get_all_violations(self):
        """Get all recorded violations"""
        return self.violations
    
    def get_violations_by_type(self, violation_type):
        """Get violations of specific type"""
        return [v for v in self.violations if v['type'] == violation_type]
    
    def reset(self):
        """Reset all tracking data"""
        self.violations.clear()
        self.violation_counts.clear()
        self.last_alert_time.clear()
        self.alert_count = 0
