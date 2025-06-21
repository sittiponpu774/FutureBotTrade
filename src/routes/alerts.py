from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.user import db
from src.models.trading import Alert
from datetime import datetime
import requests

alerts_bp = Blueprint("alerts", __name__)

TELEGRAM_BOT_TOKEN = '7675677081:AAE-SiMRd2Y3SLTf_7qyZdrl4cXVQqzbtik'
TELEGRAM_CHAT_ID = '444764489'

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Telegram send error:", e)

@alerts_bp.route("/alerts", methods=["GET"])
@cross_origin()
def get_all_alerts():
    try:
        alerts = Alert.query.order_by(Alert.triggered_at.desc()).limit(50).all()
        output = []
        for alert in alerts:
            output.append({
                "id": alert.id,
                "position_id": alert.position_id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "triggered_at": alert.triggered_at,
                "is_read": alert.is_read
            })
        return jsonify(output), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route("/alert/<int:alert_id>/mark-read", methods=["PUT"])
@cross_origin()
def mark_alert_read(alert_id):
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404

        alert.is_read = True
        db.session.commit()

        return jsonify({"message": f"Alert {alert_id} marked as read"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@alerts_bp.route("/alerts/clear", methods=["DELETE"])
@cross_origin()
def clear_all_alerts():
    """เคลียร์ Alerts ทั้งหมด"""
    try:
        # ลบ Alerts ทั้งหมด
        deleted_count = Alert.query.delete()
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"ลบ {deleted_count} alerts เรียบร้อยแล้ว"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@alerts_bp.route("/alerts", methods=["POST"])
@cross_origin()
def create_alert():
    try:
        data = request.get_json()
        # แปลง timestamp string เป็น datetime object
        timestamp_str = data.get("timestamp")
        triggered_at = None
        if timestamp_str:
            try:
                # รองรับทั้งแบบมี/ไม่มี 'Z'
                if timestamp_str.endswith('Z'):
                    triggered_at = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    triggered_at = datetime.fromisoformat(timestamp_str)
            except Exception:
                triggered_at = datetime.utcnow()
        else:
            triggered_at = datetime.utcnow()

        alert = Alert(
            position_id=data.get("position_id"),
            alert_type=data.get("alert_type"),
            message=data.get("message"),
            triggered_at=triggered_at,
            is_read=False
        )
        db.session.add(alert)
        db.session.commit()

        # ส่งข้อความไป Telegram
        send_telegram_alert(f"🔔 แจ้งเตือนใหม่: {alert.message}")

        return jsonify({"success": True, "alert_id": alert.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

