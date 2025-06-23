# WebSocket Integration Design Document

## การวิเคราะห์ WebSocket Technology

### ข้อมูลพื้นฐานเกี่ยวกับ WebSocket
WebSocket เป็นเทคโนโลยีที่ช่วยให้เกิดการสื่อสารแบบ real-time ระหว่าง client และ server โดยมีคุณสมบัติดังนี้:

1. **Full-duplex Communication**: สามารถส่งข้อมูลได้ทั้งสองทิศทางพร้อมกัน
2. **Persistent Connection**: การเชื่อมต่อคงอยู่ไม่ต้องสร้างใหม่ทุกครั้ง
3. **Low Latency**: ความล่าช้าต่ำเหมาะสำหรับ real-time applications
4. **Efficient**: ใช้ bandwidth น้อยกว่า HTTP polling

### Flask-SocketIO
สำหรับ Flask application เราจะใช้ Flask-SocketIO ซึ่งเป็น extension ที่:
- รองรับ WebSocket protocol
- มี fallback ไปยัง HTTP long-polling หาก WebSocket ไม่พร้อมใช้งาน
- รองรับ event-based communication
- มี built-in support สำหรับ rooms และ namespaces

## การออกแบบ WebSocket Architecture

### 1. Server-side Architecture
```
Flask Application
├── WebSocket Server (Flask-SocketIO)
├── Background Tasks (Price Updates)
├── Database (Positions, Alerts, Prices)
└── API Endpoints (REST + WebSocket)
```

### 2. Client-side Architecture
```
Frontend (HTML/JS)
├── WebSocket Client (Socket.IO)
├── UI Components (Price Display, Position Cards)
├── Event Handlers (Price Updates, Alerts)
└── State Management (Real-time Data)
```

### 3. Message Protocol Design

#### Price Update Messages
```json
{
  "type": "price_update",
  "data": {
    "symbol": "BTC/USDT",
    "price": 45000.50,
    "change_24h": 2.5,
    "timestamp": "2025-06-18T08:00:00Z"
  }
}
```

#### Position Update Messages
```json
{
  "type": "position_update",
  "data": {
    "position_id": 123,
    "symbol": "BTC/USDT",
    "entry_price": 44000.00,
    "current_price": 45000.50,
    "pnl": 1000.50,
    "pnl_percentage": 2.27,
    "status": "open"
  }
}
```

#### Alert Messages
```json
{
  "type": "alert",
  "data": {
    "alert_id": 456,
    "position_id": 123,
    "alert_type": "PROFIT_TARGET",
    "message": "Position BTC/USDT reached profit target of 2%",
    "timestamp": "2025-06-18T08:00:00Z"
  }
}
```

#### Signal Reversal Messages
```json
{
  "type": "signal_reversal",
  "data": {
    "symbol": "BTC/USDT",
    "previous_signal": "LONG",
    "new_signal": "SHORT",
    "confidence": 0.85,
    "timestamp": "2025-06-18T08:00:00Z"
  }
}
```

## การ Integrate WebSocket กับระบบเดิม

### 1. Backend Integration Points

#### A. Price Monitoring Service
- เชื่อมต่อกับ Binance WebSocket API
- รับข้อมูลราคาแบบ real-time
- ส่งต่อข้อมูลไปยัง connected clients

#### B. Position Monitoring Service
- ติดตาม positions ที่ active
- คำนวณ PnL แบบ real-time
- ส่ง updates เมื่อมีการเปลี่ยนแปลง

#### C. Alert System Integration
- ตรวจสอบเงื่อนไขการแจ้งเตือน
- ส่ง alerts ผ่าน WebSocket
- อัปเดตสถานะการอ่าน

#### D. Signal Detection Service
- ติดตาม signal changes
- ส่งการแจ้งเตือนเมื่อมีการกลับตัว

### 2. Frontend Integration Points

#### A. Real-time Price Display
- แสดงราคาปัจจุบันแบบ real-time
- อัปเดต UI โดยไม่ต้อง refresh
- แสดง price charts แบบ live

#### B. Position Cards Updates
- อัปเดต PnL แบบ real-time
- เปลี่ยนสีตามสถานะกำไร/ขาดทุน
- แสดงสถานะ position แบบ live

#### C. Alert Notifications
- แสดง popup notifications
- อัปเดต alert list แบบ real-time
- เล่นเสียงแจ้งเตือน (optional)

#### D. Signal Reversal Indicators
- แสดงสัญญาณการกลับตัว
- อัปเดต prediction results
- แจ้งเตือนการเปลี่ยนแปลงสัญญาณ

## Technical Implementation Plan

### 1. Dependencies ที่ต้องเพิ่ม
```
flask-socketio==5.3.6
python-socketio==5.9.0
websocket-client==1.6.4
```

### 2. Server-side Components

#### A. WebSocket Server Setup
```python
from flask_socketio import SocketIO, emit
socketio = SocketIO(app, cors_allowed_origins="*")
```

#### B. Event Handlers
- `connect`: จัดการการเชื่อมต่อ
- `disconnect`: จัดการการตัดการเชื่อมต่อ
- `subscribe_symbol`: สมัครรับข้อมูลเหรียญ
- `unsubscribe_symbol`: ยกเลิกการสมัครรับข้อมูล

#### C. Background Services
- Price streaming service
- Position monitoring service
- Alert checking service

### 3. Client-side Components

#### A. WebSocket Client Setup
```javascript
const socket = io();
```

#### B. Event Listeners
- `price_update`: อัปเดตราคา
- `position_update`: อัปเดต position
- `alert`: แสดงการแจ้งเตือน
- `signal_reversal`: แสดงการกลับตัวสัญญาณ

#### C. UI Update Functions
- `updatePriceDisplay()`
- `updatePositionCard()`
- `showAlert()`
- `updateSignalIndicator()`

## Performance Considerations

### 1. Connection Management
- จำกัดจำนวน concurrent connections
- ใช้ connection pooling
- จัดการ reconnection logic

### 2. Data Throttling
- จำกัดความถี่ของ price updates
- ใช้ debouncing สำหรับ UI updates
- Batch multiple updates เมื่อเป็นไปได้

### 3. Memory Management
- จำกัดขนาดของ message queues
- ทำความสะอาด inactive connections
- ใช้ efficient data structures

## Security Considerations

### 1. Authentication
- ตรวจสอบ session ก่อนอนุญาต WebSocket connection
- ใช้ JWT tokens สำหรับ authentication

### 2. Rate Limiting
- จำกัดจำนวน messages ต่อ connection
- ป้องกัน spam และ abuse

### 3. Data Validation
- ตรวจสอบ message format
- Sanitize input data
- ป้องกัน injection attacks

## Testing Strategy

### 1. Unit Tests
- ทดสอบ WebSocket event handlers
- ทดสอบ message formatting
- ทดสอบ data validation

### 2. Integration Tests
- ทดสอบการเชื่อมต่อ WebSocket
- ทดสอบ real-time data flow
- ทดสอบ error handling

### 3. Load Tests
- ทดสอบ concurrent connections
- ทดสอบ message throughput
- ทดสอบ memory usage

## Deployment Considerations

### 1. Server Requirements
- รองรับ WebSocket protocol
- เพียงพอสำหรับ concurrent connections
- มี monitoring และ logging

### 2. Scaling Strategy
- ใช้ Redis สำหรับ message broadcasting
- Load balancing สำหรับ multiple instances
- Horizontal scaling เมื่อจำเป็น

### 3. Monitoring
- ติดตาม connection counts
- Monitor message rates
- Track error rates และ latency

