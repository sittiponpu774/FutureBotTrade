from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from src.models.user import db
from src.models.trading import Alert

alerts_bp = Blueprint("alerts", __name__)

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
                "triggered_at": alert.triggered_at.isoformat(),
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

