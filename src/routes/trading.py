from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.user import db
from src.models.trading import Position, Alert, SignalHistory
from datetime import datetime
import ccxt
from src.utils.binance_websocket import get_binance_ws_client

trading_bp = Blueprint("trading", __name__)

@trading_bp.route("/track-position", methods=["POST"])
@cross_origin()
def track_position():
    print(f"[DEBUG] 🧪 เช็ค position: ")
    try:
        data = request.get_json()
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        position_type = data.get("position_type")
        entry_price = data.get("entry_price")
        profit_target = data.get("profit_target", 2.0)
        loss_limit = data.get("loss_limit", 1.0)

        if not all([symbol, timeframe, position_type, entry_price, profit_target, loss_limit]):
            return jsonify({"error": "Missing data for tracking position"}), 400

        # ✅ 1. บันทึกลงฐานข้อมูล
        new_position = Position(
            symbol=symbol,
            timeframe=timeframe,
            position_type=position_type,
            entry_price=entry_price,
            entry_time=datetime.utcnow(),
            profit_target=profit_target,
            loss_limit=loss_limit,
        )
        db.session.add(new_position)
        db.session.commit()

        
        # ✅ 2. Subscribe WebSocket ด้วย symbol + timeframe
        binance_client = get_binance_ws_client()
        binance_client.subscribe_symbol(symbol, timeframe=timeframe)

        return jsonify({
            "message": "Position tracked and WebSocket subscribed successfully",
            "position_id": new_position.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@trading_bp.route("/positions", methods=["GET"])
@cross_origin()
def get_positions():
    try:
        exchange = ccxt.binance()
        positions = Position.query.order_by(Position.created_at.desc()).all()
        output = []

        for pos in positions:
            # ดึงราคาจาก Binance แบบ real-time
            ticker = exchange.fetch_ticker(pos.symbol)
            current_price = ticker["last"]

            # คำนวณกำไร/ขาดทุน
            pnl_percent = 0
            if pos.position_type == "LONG":
                pnl_percent = ((current_price - pos.entry_price) / pos.entry_price) * 100
            elif pos.position_type == "SHORT":
                pnl_percent = ((pos.entry_price - current_price) / pos.entry_price) * 100

            output.append({
                "id": pos.id,
                "symbol": pos.symbol,
                "timeframe": pos.timeframe,
                "position_type": pos.position_type,
                "entry_price": pos.entry_price,
                "entry_time": pos.entry_time,
                "current_price": current_price,
                "current_pnl_percent": pnl_percent,
                "status": pos.status,
                "profit_target": pos.profit_target,
                "loss_limit": pos.loss_limit,
                "created_at": pos.created_at,
                "updated_at": pos.updated_at
            })

        return jsonify(output), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@trading_bp.route("/position/<int:position_id>/alerts", methods=["GET"])
@cross_origin()
def get_position_alerts(position_id):
    try:
        alerts = Alert.query.filter_by(position_id=position_id).all()
        output = []
        for alert in alerts:
            output.append({
                "id": alert.id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "is_read": alert.is_read
            })
        return jsonify(output), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trading_bp.route("/positions/clear", methods=["DELETE"])
@cross_origin()
def clear_all_positions():
    """เคลียร์ Positions ทั้งหมด"""
    try:
        # ลบ Positions ทั้งหมด
        deleted_count = Position.query.delete()
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"ลบ {deleted_count} positions เรียบร้อยแล้ว"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@trading_bp.route("/price-history", methods=["GET"])
@cross_origin()
def price_history():
    """
    ตัวอย่าง: /api/price-history?symbol=DOGEUSDT&limit=50&timeframe=1m
    """
    print(f"[DEBUG] 🧪 เช็ค chart: ")
    try:
        symbol = request.args.get("symbol")
        limit = int(request.args.get("limit", 50))
        timeframe = request.args.get("timeframe")

        if not symbol:
            return jsonify({"error": "Missing symbol"}), 400

        exchange = ccxt.binance()
        if "/" not in symbol:
            symbol_ccxt = symbol.replace("USDT", "/USDT")
        else:
            symbol_ccxt = symbol

        ohlcv = exchange.fetch_ohlcv(symbol_ccxt, timeframe=timeframe, limit=limit)
        result = [
            {
                "timestamp": ts,
                "open": open_,
                "high": high,
                "low": low,
                "close": close
            }
            for ts, open_, high, low, close, vol in ohlcv
        ]
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@trading_bp.route("/positions/<int:position_id>", methods=["DELETE"])
@cross_origin()
def delete_position(position_id):
    """ลบ Position รายตัวตาม id"""
    try:
        pos = Position.query.get(position_id)
        if not pos:
            return jsonify({"error": "ไม่พบ Position นี้"}), 404
        db.session.delete(pos)
        db.session.commit()
        return jsonify({"success": True, "message": f"ลบ Position {position_id} เรียบร้อยแล้ว"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def create_position(symbol, timeframe, position_type, entry_price, entry_time=None, profit_target=2.0, loss_limit=1.0, telegram_user=None):
    """
    ฟังก์ชันสร้าง Position สำหรับเรียกใช้จาก Telegram bot โดยตรง
    """
    try:
        new_position = Position(
            symbol=symbol,
            timeframe=timeframe,
            position_type=position_type,
            entry_price=entry_price,
            entry_time=entry_time or datetime.utcnow(),
            profit_target=profit_target,
            loss_limit=loss_limit,
            telegram_user=telegram_user
        )
        db.session.add(new_position)
        db.session.commit()
        return {"success": True, "position_id": new_position.id}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
