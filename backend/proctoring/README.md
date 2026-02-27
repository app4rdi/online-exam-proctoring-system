# Proctoring System - AI Exam Monitoring

## 📋 Tổng quan

Module proctoring cung cấp giám sát thi tự động sử dụng AI:
- **Face Detection**: Phát hiện khuôn mặt, đếm số người
- **Object Detection**: Phát hiện vật cấm (điện thoại, sách, laptop...)
- **Violation Tracking**: Theo dõi vi phạm và cảnh báo
- **Screenshot Manager**: Lưu ảnh vi phạm

## 📁 Cấu trúc

```
backend/proctoring/
├── __init__.py
├── proctoring_system.py      # Main orchestrator
├── detectors/                 # Detection modules
│   ├── __init__.py
│   ├── face_detector.py      # OpenCV face detection
│   └── object_detector.py    # YOLO object detection
├── utils/                     # Utilities
│   ├── __init__.py
│   ├── violation_tracker.py  # Track violations
│   └── screenshot_manager.py # Save screenshots
└── models/                    # Pre-trained models folder
```

## 🔧 Dependencies

```bash
pip install opencv-python torch ultralytics numpy
```

## 🎯 Models Required

Đặt các file model vào thư mục root:

1. **Face Detection** (OpenCV DNN):
   - `deploy.prototxt`
   - `res10_300x300_ssd_iter_140000.caffemodel`

2. **Object Detection** (YOLO):
   - `yolov8n.pt` hoặc `yolov5su.pt`

## 💻 Usage

### 1. Khởi tạo hệ thống

```python
from backend.proctoring.proctoring_system import ProctoringSystem

# Tạo proctoring system
proctor = ProctoringSystem(
    student_id=123,
    exam_id=456,
    face_confidence=0.5,
    object_confidence=0.5,
    violation_threshold=3
)
```

### 2. Xử lý video frame

```python
import cv2

# Đọc frame từ webcam
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

# Xử lý frame
results = proctor.process_frame(frame)

print(results)
# {
#     'timestamp': '2024-...',
#     'student_id': 123,
#     'exam_id': 456,
#     'face_count': 1,
#     'prohibited_items': ['cell phone'],
#     'violations': [...],
#     'status': 'alert'
# }
```

### 3. Lấy thống kê

```python
# Thống kê tổng quan
stats = proctor.get_statistics()
print(stats)

# Báo cáo chi tiết
report = proctor.get_violations_report()

# Lưu báo cáo
proctor.save_report('report.json')
```

## 🌐 API Endpoints

### Start Session
```javascript
POST /api/proctoring/start-session
Body: { exam_id: 123 }
```

### Process Frame
```javascript
POST /api/proctoring/process-frame
Body: {
    exam_id: 123,
    frame: "data:image/jpeg;base64,..."
}
```

### Get Statistics
```javascript
GET /api/proctoring/get-statistics?exam_id=123
```

### End Session
```javascript
POST /api/proctoring/end-session
Body: { exam_id: 123 }
```

### Teacher Monitor (Real-time)
```javascript
GET /api/proctoring/teacher/monitor/123
```

## 🎨 Frontend Integration

```javascript
// Khởi tạo webcam
const video = document.getElementById('webcam');
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
video.srcObject = stream;

// Bắt đầu session
await fetch('/api/proctoring/start-session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ exam_id: 123 })
});

// Gửi frame định kỳ (mỗi 2 giây)
setInterval(async () => {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    const frame = canvas.toDataURL('image/jpeg');
    
    const response = await fetch('/api/proctoring/process-frame', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ exam_id: 123, frame })
    });
    
    const data = await response.json();
    
    if (data.results.status === 'alert') {
        showViolationAlert(data.results.violations);
    }
}, 2000);
```

## ⚙️ Configuration

### Violation Types

- `no_face`: Không phát hiện khuôn mặt
- `multiple_faces`: Nhiều người trong frame
- `prohibited_object`: Phát hiện vật cấm

### Prohibited Items

```python
PROHIBITED_ITEMS = [
    "cell phone",
    "book",
    "laptop", 
    "tablet",
    "keyboard",
    "mouse",
    "remote"
]
```

### Thresholds

- `violation_threshold=3`: Số lần vi phạm trước khi cảnh báo
- `cooldown_seconds=10`: Thời gian giữa các cảnh báo
- `face_confidence=0.5`: Độ tin cậy phát hiện mặt
- `object_confidence=0.5`: Độ tin cậy phát hiện vật thể

## 📊 Violation Report Format

```json
{
  "student_id": 123,
  "exam_id": 456,
  "start_time": "2024-...",
  "end_time": "2024-...",
  "statistics": {
    "total_violations": 15,
    "violations_by_type": {
      "no_face": 5,
      "multiple_faces": 3,
      "prohibited_object": 7
    },
    "alerts_triggered": 3
  },
  "violations": [
    {
      "type": "prohibited_object",
      "message": "cell phone detected",
      "timestamp": "2024-...",
      "count": 1,
      "alert": false
    }
  ]
}
```

## 🎯 Features

✅ **Real-time Detection**
- Face detection với OpenCV DNN
- Object detection với YOLO
- Sub-second processing

✅ **Smart Alerting**
- Threshold-based alerts
- Cooldown để tránh spam
- Multi-level severity

✅ **Evidence Collection**
- Auto-save violation screenshots
- Timestamped evidence
- Student-specific folders

✅ **Teacher Dashboard**
- Monitor tất cả học sinh real-time
- View violations live
- Export reports

## 🔒 Security

- Session-based authentication
- Student ID verification
- Encrypted frame transmission
- Secure screenshot storage

## 📈 Performance

- **Face Detection**: ~30ms/frame (CPU)
- **Object Detection**: ~50-100ms/frame (CPU), ~10ms (GPU)
- **Memory**: ~500MB với YOLO model loaded
- **Bandwidth**: ~2-5 KB/frame (compressed JPEG)

## 🚀 Future Enhancements

- [ ] Eye gaze tracking
- [ ] Audio detection (talking, noise)
- [ ] Screen recording detection
- [ ] Browser tab switching detection
- [ ] Pose estimation
- [ ] Emotion detection
- [ ] Real-time streaming to teacher
- [ ] ML-based anomaly detection
