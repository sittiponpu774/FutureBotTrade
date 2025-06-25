import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import asyncio
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from src.app import db, app
from src.models.user import User
from src.routes.user import user_bp
from src.routes.predict import predict_bp
from src.routes.trading import trading_bp
from src.routes.alerts import alerts_bp
from src.models.trading import Position, Alert, SignalHistory
from src.tasks.background_tasks import start_background_tasks
from src.websocket.websocket_server import init_websocket
from src.utils.binance_websocket import get_binance_ws_client
import threading
from src.telegram_bot import build_bot


# ไม่จำเป็นต้องมีฟังก์ชันนี้แล้ว เพราะเราจะใช้ asyncio.run ในเธรด
# def run_telegram_bot():
#     print("[DEBUG] เรียก telegram bot แล้ว")
#     start_telegram_bot()

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(predict_bp, url_prefix="/api")
app.register_blueprint(trading_bp, url_prefix="/api")
app.register_blueprint(alerts_bp, url_prefix="/api")

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all() # This will create all tables defined in db.Model subclasses

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

def run_telegram_bot_background():
    try:
        telegram_app = build_bot(socketio)  # ✅ ชื่อไม่ซ้ำกับ Flask app
        print("[DEBUG] เริ่ม Telegram Bot...")

        # 🔧 สร้าง event loop ใหม่ในเธรดนี้
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 🔁 รัน bot แบบ async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(telegram_app.run_polling())  # ✅ ทำงานได้ถูกต้อง

    except Exception as e:
        print(f"[ERROR] Telegram Bot error: {e}")
        
def subscribe_position(position):
    try:
        client = get_binance_ws_client()
        client.subscribe_symbol(position.symbol, position.timeframe)
    except Exception as e:
        print(f"[ERROR] subscribe_position: {e}")

# def subscribe_existing_positions():
#     """ดึง Positions ที่เคย track แล้วมาสมัคร WebSocket อีกครั้ง"""
#     try:
#         client = get_binance_ws_client()
#         positions = Position.query.all()
#         for pos in positions:
#             client.subscribe_symbol(pos.symbol, timeframe=pos.timeframe)
#         print(f"[DEBUG] ✅ Subscribed {len(positions)} positions จาก DB แล้ว")
#     except Exception as e:
#         print(f"[ERROR] subscribe_existing_positions: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    init_websocket(socketio)
    binance_client = get_binance_ws_client(socketio)
    start_background_tasks(app, socketio)
    # subscribe_existing_positions()  # 🟢 เรียกก่อนรันแอป
    binance_client.connect()

    common_symbols = ['BTCUSDT', 'ETHUSDT', 'DOGEUSDT', 'ADAUSDT', 'SOLUSDT']
    for symbol in common_symbols:
        binance_client.subscribe_symbol(symbol)

    # ✅ ใช้ threading.Thread เพื่อสั่งรัน async function ใน background อย่างถูกต้อง
    telegram_thread = threading.Thread(target=run_telegram_bot_background)
    telegram_thread.daemon = True # ทำให้เธรดนี้หยุดทำงานเมื่อโปรแกรมหลักจบ
    telegram_thread.start()

    # เริ่ม Flask + SocketIO
    # *** สำคัญ: ปิด debug และ reloader เพื่อหลีกเลี่ยงปัญหาเรื่อง process spawning ***
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)