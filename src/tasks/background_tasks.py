from flask import Flask
from threading import Thread
import time
from src.app import db, app
from src.models.user import User
from src.models.trading import Position, Alert
from datetime import datetime
import ccxt
from src.websocket.price_streaming import get_price_streaming_service
from src.websocket.position_monitoring import get_position_monitoring_service

def update_positions_task(app):
    with app.app_context():
        while True:
            with app.app_context():
                print("Running background task: Updating positions...")
                active_positions = Position.query.filter_by(status="ACTIVE").all()
                exchange = ccxt.binance({
                    "sandbox": False,
                    "rateLimit": 1200,
                    "enableRateLimit": True,
                })

                for pos in active_positions:
                    try:
                        # 🔁 โหลดอีกรอบ เพื่อเช็คว่า object ยังมีอยู่
                        fresh_pos = Position.query.get(pos.id)
                        if fresh_pos is None:
                            continue  # skip ถ้าโดนลบไปแล้ว

                        ticker = exchange.fetch_ticker(fresh_pos.symbol)
                        latest_price = ticker["last"]

                        fresh_pos.current_price = latest_price
                        pnl_percent = 0
                        if fresh_pos.position_type == "LONG":
                            pnl_percent = ((latest_price - fresh_pos.entry_price) / fresh_pos.entry_price) * 100
                        elif fresh_pos.position_type == "SHORT":
                            pnl_percent = ((fresh_pos.entry_price - latest_price) / fresh_pos.entry_price) * 100
                        fresh_pos.current_pnl_percent = pnl_percent

                        if pnl_percent >= fresh_pos.profit_target:
                            alert_message = f"ถึงเป้าหมายกำไร! Position ID: {fresh_pos.id}, {fresh_pos.symbol} {fresh_pos.timeframe}: กำไร {pnl_percent:.2f}%"
                            new_alert = Alert(
                                position_id=fresh_pos.id,
                                alert_type="PROFIT_TARGET",
                                message=alert_message,
                                triggered_at=datetime.utcnow()
                            )
                            db.session.add(new_alert)
                            fresh_pos.status = "CLOSED"

                        elif pnl_percent <= -fresh_pos.loss_limit:
                            alert_message = f"ถึงขีดจำกัดขาดทุน! Position ID: {fresh_pos.id}, {fresh_pos.symbol} {fresh_pos.timeframe}: ขาดทุน {pnl_percent:.2f}%"
                            new_alert = Alert(
                                position_id=fresh_pos.id,
                                alert_type="LOSS_LIMIT",
                                message=alert_message,
                                triggered_at=datetime.utcnow()
                            )
                            db.session.add(new_alert)
                            fresh_pos.status = "CLOSED"

                        db.session.commit()

                    except Exception as e:
                        print(f"Error updating position {pos.id if pos else 'unknown'}: {e}")
                        db.session.rollback()

                time.sleep(10) # Run every 60 seconds

def start_background_tasks(app, socketio):
    """Start all background tasks including WebSocket services"""
    
    # Start original background task
    thread = Thread(target=update_positions_task, args=(app,))
    thread.daemon = True
    thread.start()
    
    # Start WebSocket services
    price_service = get_price_streaming_service(app, socketio)
    price_service.start()
    
    position_service = get_position_monitoring_service(app, socketio)
    position_service.start()
    
    print("All background tasks and WebSocket services started")


