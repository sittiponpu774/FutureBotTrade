# Crypto Price Predictor v3.0 - WebSocket Edition

แอปพลิเคชันวิเคราะห์และทำนายราคา Cryptocurrency ที่มีความสามารถครบครันและทันสมัย พร้อมฟีเจอร์ Real-time WebSocket

## 🚀 ฟีเจอร์หลัก

### 🎯 **การทำนายราคาด้วย AI**
- ใช้ XGBoost Machine Learning Algorithm
- วิเคราะห์ Technical Indicators (MA, RSI, MACD)
- ทำนายทิศทาง Long/Short พร้อมความแม่นยำ
- รองรับหลายเหรียญ: BTC, ETH, DOGE, ADA, SOL
- เลือก Timeframe ได้: 1h, 4h, 1d

### 💼 **ระบบจัดการ Position**
- สร้าง Position อัตโนมัติจากผลการทำนาย
- ติดตามกำไร/ขาดทุนแบบ Real-time
- กำหนดเป้าหมายกำไร (default: 2%)
- ตั้งขีดจำกัดขาดทุน (default: 1%)
- ปิด Position อัตโนมัติเมื่อถึงเป้าหมาย

### 🔔 **ระบบการแจ้งเตือนอัตโนมัติ**
- **จุดกลับตัว**: แจ้งเตือนเมื่อสัญญาณเปลี่ยนจาก Long เป็น Short
- **เป้าหมายกำไร**: แจ้งเตือนเมื่อกำไรถึงเป้าหมาย
- **ขีดจำกัดขาดทุน**: แจ้งเตือนเมื่อขาดทุนเกินกำหนด
- การแจ้งเตือนแบบ Real-time ผ่าน WebSocket

### ⚡ **WebSocket Real-time Features**
- **Live Price Updates**: ราคาอัปเดตแบบ Real-time
- **Position Monitoring**: ติดตามสถานะ Position แบบทันที
- **Instant Alerts**: การแจ้งเตือนแบบ Real-time
- **Signal Reversal Detection**: ตรวจจับการเปลี่ยนแปลงสัญญาณทันที
- **Connection Status**: แสดงสถานะการเชื่อมต่อ WebSocket

### 🎨 **User Interface**
- UI สวยงามด้วย Gradient Design
- Responsive Design รองรับทั้งมือถือและคอมพิวเตอร์
- Tab-based Navigation
- Real-time Status Indicators
- Loading Animations และ Error Handling

## 📋 ความต้องการระบบ

- Python 3.8+
- Flask และ Flask-SocketIO
- XGBoost, Scikit-learn
- CCXT (สำหรับ Cryptocurrency API)
- SQLite (สำหรับ Database)

## 🔧 การติดตั้ง

1. **แตกไฟล์โปรเจค**
```bash
tar -xzf crypto_predictor_v3_websocket.tar.gz
cd crypto_predictor
```

2. **สร้าง Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# หรือ venv\Scripts\activate  # Windows
```

3. **ติดตั้ง Dependencies**
```bash
pip install -r requirements.txt
```

4. **รันแอปพลิเคชัน**
```bash
python src/main.py
```

5. **เปิดเบราว์เซอร์**
```
http://localhost:5000
```

## 🎮 วิธีการใช้งาน

### การทำนายราคา
1. เลือกเหรียญที่ต้องการ (BTC/USDT, ETH/USDT, etc.)
2. เลือก Timeframe (1h, 4h, 1d)
3. คลิก "ทำนายราคา"
4. ดูผลการทำนาย Long/Short พร้อมความแม่นยำ

### การจัดการ Position
1. คลิกแท็บ "จัดการ Positions"
2. ดู Position ที่เปิดอยู่
3. ติดตามกำไร/ขาดทุนแบบ Real-time
4. Position จะปิดอัตโนมัติเมื่อถึงเป้าหมาย

### การดูการแจ้งเตือน
1. คลิกแท็บ "การแจ้งเตือน"
2. ดูประวัติการแจ้งเตือนทั้งหมด
3. ติดตามการแจ้งเตือนแบบ Real-time

## 🔌 WebSocket Features

### การเชื่อมต่อ
- แอปพลิเคชันจะเชื่อมต่อ WebSocket อัตโนมัติ
- สถานะการเชื่อมต่อแสดงที่มุมบนขวา
- 🟢 เชื่อมต่อแล้ว / 🔴 ขาดการเชื่อมต่อ

### Real-time Events
- `price_update`: อัปเดตราคาแบบ Real-time
- `position_update`: อัปเดตสถานะ Position
- `new_alert`: การแจ้งเตือนใหม่
- `signal_reversal`: การเปลี่ยนแปลงสัญญาณ

## ⚠️ หมายเหตุสำคัญ

### การใช้งาน Mock Data
- เนื่องจากข้อจำกัดของ Binance API ในบางภูมิภาค
- แอปพลิเคชันจะใช้ Mock Exchange เมื่อไม่สามารถเชื่อมต่อ Binance ได้
- Mock Data จะจำลองการเคลื่อนไหวของราคาแบบสมจริง

### การใช้งานจริง
- สำหรับการใช้งานจริง ควรใช้ VPN หรือ Proxy
- หรือปรับแต่งให้ใช้ Exchange อื่นๆ ที่รองรับ

### ข้อจำกัดความรับผิดชอบ
- แอปพลิเคชันนี้พัฒนาเพื่อการศึกษาและการทดลอง
- ไม่ใช่คำแนะนำการลงทุน
- ผู้ใช้ควรศึกษาและประเมินความเสี่ยงด้วยตนเอง

## 🛠️ การปรับแต่ง

### การเปลี่ยนเป้าหมายกำไร/ขาดทุน
แก้ไขไฟล์ `src/routes/trading.py`:
```python
PROFIT_TARGET = 0.02  # 2% กำไร
LOSS_LIMIT = 0.01     # 1% ขาดทุน
```

### การเพิ่มเหรียญใหม่
แก้ไขไฟล์ `src/utils/mock_exchange.py`:
```python
self.symbols = {
    'BTC/USDT': {'price': 45000, 'change': 0},
    'NEW/USDT': {'price': 100, 'change': 0},  # เพิ่มเหรียญใหม่
}
```

## 📁 โครงสร้างโปรเจค

```
crypto_predictor/
├── src/
│   ├── main.py                 # Flask Application
│   ├── models/                 # Database Models
│   ├── routes/                 # API Routes
│   ├── static/                 # Frontend Files
│   ├── tasks/                  # Background Tasks
│   ├── utils/                  # Utilities
│   └── websocket/              # WebSocket Services
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
└── *.md                       # Design Documents
```

## 🔄 การอัปเดต

### v3.0 - WebSocket Edition
- เพิ่ม Real-time WebSocket functionality
- Live price updates
- Real-time position monitoring
- Instant alerts และ notifications
- Signal reversal detection
- Mock Exchange fallback

### v2.0 - Position Management
- ระบบจัดการ Position
- การแจ้งเตือนอัตโนมัติ
- การคำนวณกำไร/ขาดทุน
- จุดกลับตัวสัญญาณ

### v1.0 - Basic Prediction
- การทำนายราคาพื้นฐาน
- UI เบื้องต้น
- ML Model integration

## 🆘 การแก้ไขปัญหา

### WebSocket ไม่เชื่อมต่อ
1. ตรวจสอบว่า Flask server รันอยู่
2. ตรวจสอบ port 5000 ว่าไม่ถูกใช้งาน
3. รีเฟรชหน้าเว็บ

### การทำนายไม่ทำงาน
1. ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต
2. ระบบจะใช้ Mock Data อัตโนมัติหากไม่สามารถเชื่อมต่อ API ได้

### Database Error
1. ลบไฟล์ `instance/database.db`
2. รีสตาร์ทแอปพลิเคชัน

## 📞 การสนับสนุน

หากพบปัญหาหรือต้องการความช่วยเหลือ:
1. ตรวจสอบ Console logs ในเบราว์เซอร์
2. ตรวจสอบ Server logs ใน Terminal
3. อ่านเอกสารการออกแบบใน `DESIGN_DOCUMENT.md`

---

**Crypto Price Predictor v3.0** - Powered by AI, Enhanced with WebSocket Real-time Technology

#   F u t u r e B o t T r a d e  
 #   F u t u r e B o t T r a d e  
 #   F u t u r e B o t T r a d e  
 #   F u t u r e B o t T r a d e  
 