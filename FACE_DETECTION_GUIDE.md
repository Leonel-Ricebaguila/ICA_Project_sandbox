# ICA Face Detection System Guide

This guide covers the enhanced camera monitoring system with face detection capabilities using OpenCV pre-trained models.

## 🎯 Features

### Face Detection Capabilities
- **Real-time face detection** using OpenCV Haar cascades
- **Eye detection** within detected faces
- **Smile detection** for emotion analysis
- **Confidence scoring** for detection accuracy
- **Face counting** and statistics tracking
- **Data logging** to CSV files and server

### Enhanced Camera System
- **Multiple camera support** with individual face detection
- **Real-time annotations** on video streams
- **Screenshot functionality** with face detection overlays
- **Statistics display** and data export
- **Server integration** for centralized logging

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_unified.txt
```

### 2. Start the Server

```bash
python NFC_ServerSide/server_unified.py
```

### 3. Run Face Detection Camera System

```bash
python camaras_face_detection.py
```

## 🎮 Controls

When running the camera system, use these keyboard controls:

- **ESC** - Exit the camera system
- **S** - Take screenshot of all camera streams
- **F** - Toggle face detection on/off
- **D** - Display face detection statistics

## 📊 Face Detection Features

### Real-time Detection
- Detects faces in video streams every 5 frames
- Draws bounding boxes around detected faces
- Shows face count and confidence level
- Detects eyes and smiles within faces

### Visual Annotations
- **Green rectangles** - Face boundaries
- **Blue rectangles** - Eye detection
- **Red rectangles** - Smile detection
- **White text** - Face count and user information
- **Status indicators** - Detection on/off status

### Data Collection
- **Pandas DataFrame** - Stores all detection data
- **CSV export** - Saves data with timestamps
- **Server logging** - Centralized event logging
- **Statistics tracking** - Per-user and overall statistics

## 🔧 Configuration

### Face Detection Settings

In `camaras_face_detection.py`, you can modify:

```python
# Detection frequency (every N frames)
detection_interval = 60

# Window size for better detection
self.window_width = 640
self.window_height = 480

# Confidence thresholds
confidence_threshold = 0.5  # For DNN model
```

### Server Logging

The server automatically logs:
- Camera connection events
- Face detection events
- Screenshot events
- Error events

## 📈 Data Analysis

### Face Detection Statistics

The system tracks:
- **Total detections** - Number of detection events
- **Unique users** - Number of different users detected
- **Average faces per detection** - Mean faces detected per event
- **Total faces detected** - Sum of all faces detected
- **Average confidence** - Mean confidence score
- **Detection by user** - Faces detected per user

### Data Export

Face detection data is automatically saved to CSV files:
- **Filename format**: `face_detection_data_YYYYMMDD_HHMMSS.csv`
- **Columns**: timestamp, user_id, user_name, face_count, confidence
- **Location**: Same directory as the script

## 🛠️ Technical Details

### Face Detection Models

The system uses OpenCV pre-trained models:

1. **Haar Cascades** (Primary):
   - `haarcascade_frontalface_default.xml` - Face detection
   - `haarcascade_eye.xml` - Eye detection
   - `haarcascade_smile.xml` - Smile detection

2. **DNN Model** (Optional):
   - More accurate but requires additional model files
   - Falls back to Haar cascades if not available

### Performance Optimization

- **Detection interval** - Only processes every 5th frame
- **Confidence thresholds** - Filters low-confidence detections
- **Efficient processing** - Uses grayscale for feature detection
- **Memory management** - Proper cleanup of OpenCV resources

## 📝 API Endpoints

### New Server Endpoints

- `POST /log` - Log events from camera system
- `GET /logs` - Get log information
- `GET /face-detection/stats` - Get face detection statistics

### Logging Format

```json
{
  "timestamp": "2025-01-16T10:30:00",
  "event_type": "face_detected",
  "user_id": 1,
  "user_name": "Nico",
  "data": {
    "face_count": 2,
    "confidence": 0.85,
    "frame_number": 150
  }
}
```

## 🔍 Troubleshooting

### Common Issues

1. **No faces detected**:
   - Check lighting conditions
   - Ensure faces are clearly visible
   - Try adjusting confidence thresholds

2. **Poor detection accuracy**:
   - Ensure good lighting
   - Check camera resolution
   - Verify face is facing the camera

3. **Performance issues**:
   - Increase detection interval
   - Reduce window size
   - Check system resources

### Debug Mode

Enable detailed logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Example Usage

### Basic Face Detection

1. Start the server
2. Run the camera client
3. Select cameras to monitor
4. Watch real-time face detection
5. Press 'D' to see statistics
6. Press 'S' to take screenshots

### Data Analysis

```python
import pandas as pd

# Load face detection data
df = pd.read_csv('face_detection_data_20250116_103000.csv')

# Analyze detection patterns
print(df.groupby('user_name')['face_count'].sum())
print(df['confidence'].mean())
```

## 🔒 Security Considerations

- **Data privacy** - Face detection data is stored locally
- **Logging** - All events are logged for audit purposes
- **Access control** - Camera access requires valid user authentication
- **Data retention** - Consider implementing data retention policies

## 🚀 Future Enhancements

Potential improvements:
- **Face recognition** - Identify specific individuals
- **Emotion detection** - Analyze facial expressions
- **Age/gender estimation** - Demographic analysis
- **Real-time alerts** - Notifications for specific events
- **Database integration** - Store detection data in database
- **Web interface** - Browser-based monitoring

## 📞 Support

For issues and questions:
- Check the server logs (`ica_server.log`)
- Verify camera connectivity
- Test with the original camera system first
- Review face detection statistics

## 🎉 Success!

The face detection system is now fully integrated with your ICA project. You can:

- Monitor multiple cameras with real-time face detection
- Track detection statistics and export data
- Log all events to the centralized server
- Take screenshots with face detection overlays
- Analyze detection patterns over time

Enjoy your enhanced camera monitoring system! 🎥👥

