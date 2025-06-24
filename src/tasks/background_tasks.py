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
                        ticker = exchange.fetch_ticker(pos.symbol)
                        latest_price = ticker["last"]

                        pos.current_price = latest_price
                        pnl_percent = 0
                        if pos.position_type == "LONG":
                            pnl_percent = ((latest_price - pos.entry_price) / pos.entry_price) * 100
                        elif pos.position_type == "SHORT":
                            pnl_percent = ((pos.entry_price - latest_price) / pos.entry_price) * 100
                        pos.current_pnl_percent = pnl_percent

                        if pnl_percent >= pos.profit_target:
                            alert_message = f"ถึงเป้าหมายกำไร! Position ID: {pos.id}, {pos.symbol} {pos.timeframe}: กำไร {pnl_percent:.2f}%"
                            new_alert = Alert(
                                position_id=pos.id,
                                alert_type="PROFIT_TARGET",
                                message=alert_message,
                                triggered_at=datetime.utcnow()
                            )
                            db.session.add(new_alert)
                            pos.status = "CLOSED"
                        elif pnl_percent <= -pos.loss_limit:
                            alert_message = f"ถึงขีดจำกัดขาดทุน! Position ID: {pos.id}, {pos.symbol} {pos.timeframe}: ขาดทุน {pnl_percent:.2f}%"
                            new_alert = Alert(
                                position_id=pos.id,
                                alert_type="LOSS_LIMIT",
                                message=alert_message,
                                triggered_at=datetime.utcnow()
                            )
                            db.session.add(new_alert)
                            pos.status = "CLOSED"
                        db.session.commit()

                    except Exception as e:
                        print(f"Error updating position {pos.id}: {e}")
                        db.session.rollback()
                time.sleep(60) # Run every 60 seconds

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


