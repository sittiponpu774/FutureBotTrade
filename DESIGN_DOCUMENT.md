# การวิเคราะห์และออกแบบฟังก์ชันการแนะนำระยะเวลาถือครอง

## ความต้องการหลัก

### 1. การตรวจจับจุดกลับตัว (Reversal Point Detection)
- **เป้าหมาย**: ตรวจจับเมื่อสัญญาณเปลี่ยนจาก Long เป็น Short หรือ Short เป็น Long
- **วิธีการ**: เปรียบเทียบการทำนายปัจจุบันกับการทำนายก่อนหน้า
- **ข้อมูลที่ต้องเก็บ**: ประวัติการทำนาย, ราคาเริ่มต้น, เวลาเริ่มต้น

### 2. การคำนวณกำไร/ขาดทุน
- **เป้าหมายกำไร**: 2%
- **เป้าหมายขาดทุนสูงสุด**: 1%
- **การคำนวณ**: 
  - Long: (ราคาปัจจุบัน - ราคาเริ่มต้น) / ราคาเริ่มต้น * 100
  - Short: (ราคาเริ่มต้น - ราคาปัจจุบัน) / ราคาเริ่มต้น * 100

### 3. ระบบการแจ้งเตือน
- **เงื่อนไขการแจ้งเตือน**:
  1. เมื่อสัญญาณกลับตัว (Long → Short หรือ Short → Long)
  2. เมื่อถึงเป้าหมายกำไร 2%
  3. เมื่อถึงขีดจำกัดขาดทุน 1%

## ข้อมูลที่ต้องเก็บในระบบ

### Position Tracking
```python
{
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "position_type": "LONG",  # LONG หรือ SHORT
    "entry_price": 65000.0,
    "entry_time": "2025-06-18 12:00:00",
    "current_price": 66300.0,
    "current_pnl_percent": 2.0,
    "status": "ACTIVE",  # ACTIVE, CLOSED, ALERT
    "alerts": [
        {
            "type": "PROFIT_TARGET",
            "message": "ถึงเป้าหมายกำไร 2%",
            "time": "2025-06-18 13:30:00"
        }
    ]
}
```

## การออกแบบ API ใหม่

### 1. API สำหรับการติดตาม Position
- `POST /api/track-position` - เริ่มติดตาม position ใหม่
- `GET /api/positions` - ดู positions ที่กำลังติดตามอยู่
- `PUT /api/position/{id}/close` - ปิด position
- `GET /api/position/{id}/alerts` - ดูการแจ้งเตือนของ position

### 2. API สำหรับการทำนายต่อเนื่อง
- `POST /api/continuous-predict` - ทำนายและตรวจสอบการเปลี่ยนแปลงสัญญาณ
- `GET /api/signal-history/{symbol}` - ดูประวัติสัญญาณ

## การออกแบบ Database Schema

### Table: positions
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    position_type VARCHAR(5) NOT NULL,  -- LONG, SHORT
    entry_price DECIMAL(20,8) NOT NULL,
    entry_time DATETIME NOT NULL,
    current_price DECIMAL(20,8),
    current_pnl_percent DECIMAL(10,4),
    status VARCHAR(10) DEFAULT 'ACTIVE',  -- ACTIVE, CLOSED
    profit_target DECIMAL(10,4) DEFAULT 2.0,
    loss_limit DECIMAL(10,4) DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Table: alerts
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    alert_type VARCHAR(20) NOT NULL,  -- REVERSAL, PROFIT_TARGET, LOSS_LIMIT
    message TEXT NOT NULL,
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (position_id) REFERENCES positions (id)
);
```

### Table: signal_history
```sql
CREATE TABLE signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    prediction INTEGER NOT NULL,  -- 0=SHORT, 1=LONG
    price DECIMAL(20,8) NOT NULL,
    accuracy DECIMAL(10,4),
    predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## การออกแบบ UI ใหม่

### 1. หน้าหลัก (Dashboard)
- แสดงการทำนายปัจจุบัน
- แสดง positions ที่กำลังติดตามอยู่
- แสดงการแจ้งเตือนล่าสุด

### 2. หน้า Position Management
- รายการ positions ทั้งหมด
- สถานะกำไร/ขาดทุนแบบเรียลไทม์
- ปุ่มปิด position

### 3. หน้า Alerts
- รายการการแจ้งเตือนทั้งหมด
- การตั้งค่าการแจ้งเตือน

## ขั้นตอนการพัฒนา

### Phase 7: ปรับปรุงโมเดล ML และ API
1. สร้าง Database Models ใหม่
2. พัฒนา API สำหรับการติดตาม positions
3. พัฒนาระบบการทำนายต่อเนื่อง
4. สร้างระบบตรวจจับจุดกลับตัว

### Phase 8: เพิ่ม Logic การคำนวณกำไร/ขาดทุน
1. พัฒนาระบบคำนวณ PnL
2. สร้างระบบการแจ้งเตือน
3. พัฒนา Background Task สำหรับการอัปเดตราคา

### Phase 9: ปรับปรุง UI
1. ออกแบบ UI ใหม่สำหรับ Position Management
2. เพิ่มระบบการแจ้งเตือนใน UI
3. สร้างกราฟแสดงผลกำไร/ขาดทุน

## ข้อจำกัดและความเสี่ยง

### 1. ข้อจำกัดทางเทคนิค
- การทำนายต่อเนื่องต้องใช้ทรัพยากรมาก
- ความแม่นยำของการตรวจจับจุดกลับตัวอาจไม่สูง
- ข้อมูลราคาแบบเรียลไทม์อาจมีความล่าช้า

### 2. ความเสี่ยงทางการเงิน
- การทำนายไม่ได้รับประกันความแม่นยำ 100%
- ตลาดคริปโตมีความผันผวนสูง
- ผู้ใช้ควรใช้เป็นเครื่องมือช่วยตัดสินใจเท่านั้น

### 3. ข้อควรระวัง
- ต้องมีการ Disclaimer ที่ชัดเจน
- ไม่ควรใช้เป็นคำแนะนำการลงทุนเพียงอย่างเดียว
- ควรมีการทดสอบ Backtesting ก่อนใช้งานจริง

