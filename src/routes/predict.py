from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import ccxt
import pandas as pd
from datetime import datetime
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np
from src.models.user import db
from src.models.trading import SignalHistory, Alert, Position
from src.utils.mock_exchange import get_exchange

predict_bp = Blueprint("predict", __name__)

@predict_bp.route("/predict", methods=["POST"])
@cross_origin()
def predict_price():
    try:
        data = request.get_json()
        symbol = data.get("symbol", "DOGE/USDT")
        timeframe = data.get("timeframe", "1h")
        
        # Validate inputs
        if not symbol or not timeframe:
            return jsonify({"error": "Symbol และ timeframe จำเป็นต้องระบุ"}), 400
        
        # Initialize exchange with fallback to mock
        exchange = get_exchange(use_mock=False)  # Try real first, fallback to mock
        
        # Fetch historical data
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=720)
        except ccxt.NetworkError as e:
            return jsonify({"error": f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}"}), 500
        except ccxt.ExchangeError as e:
            return jsonify({"error": f"ไม่สามารถดึงข้อมูลสำหรับ {symbol} ได้: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"error": f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}"}), 500
        
        if len(ohlcv) < 50:
            return jsonify({"error": "ข้อมูลไม่เพียงพอสำหรับการทำนาย"}), 400
        
        # Create DataFrame
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        # Create features
        df["return"] = df["close"].pct_change()
        df["ma"] = df["close"].rolling(12).mean()
        df["std"] = df["close"].rolling(12).std()
        df["vol_avg"] = df["volume"].rolling(12).mean()
        
        # Create target (predict future price direction)
        future_periods = 24 if timeframe == "1h" else (6 if timeframe == "4h" else 1)
        df["future_close"] = df["close"].shift(-future_periods)
        df["target"] = (df["future_close"] > df["close"]).astype(int)
        
        # Remove NaN values
        df.dropna(inplace=True)
        
        if len(df) < 30:
            return jsonify({"error": "ข้อมูลไม่เพียงพอหลังจากการประมวลผล"}), 400
        
        # Prepare features and target
        features = ["close", "return", "ma", "std", "vol_avg"]
        X = df[features]
        y = df["target"]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)
        
        # Train model
        model = XGBClassifier(random_state=42, n_estimators=100)
        model.fit(X_train, y_train)
        
        # Calculate accuracy
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Make prediction for current data
        current_data = df[features].iloc[-1:].values
        prediction = model.predict(current_data)[0]
        
        # Get latest price
        # latest_price = float(df["close"].iloc[-1])
        ticker = exchange.fetch_ticker(symbol)
        latest_price = float(ticker["last"])


        # Save signal history
        new_signal = SignalHistory(
            symbol=symbol,
            timeframe=timeframe,
            prediction=int(prediction),
            price=latest_price,
            accuracy=float(accuracy),
            predicted_at=datetime.utcnow()
        )
        db.session.add(new_signal)
        db.session.commit()

        # Check for signal reversal
        last_signal = SignalHistory.query.filter_by(symbol=symbol, timeframe=timeframe)\
                                 .order_by(SignalHistory.predicted_at.desc()).offset(1).first()

        if last_signal and last_signal.prediction != prediction:
            # Signal reversal detected
            alert_message = f"สัญญาณเปลี่ยน! {symbol} {timeframe}: จาก {'LONG' if last_signal.prediction == 1 else 'SHORT'} เป็น {'LONG' if prediction == 1 else 'SHORT'}"
            new_alert = Alert(
                position_id=None, # This alert is not tied to a specific position yet
                alert_type="REVERSAL",
                message=alert_message,
                triggered_at=datetime.utcnow()
            )
            db.session.add(new_alert)
            db.session.commit()

        # Update active positions and check for profit/loss targets
        active_positions = Position.query.filter_by(symbol=symbol, timeframe=timeframe, status="ACTIVE").all()
        for pos in active_positions:
            pos.current_price = latest_price
            pnl_percent = 0
            if pos.position_type == "LONG":
                pnl_percent = ((latest_price - pos.entry_price) / pos.entry_price) * 100
            elif pos.position_type == "SHORT":
                pnl_percent = ((pos.entry_price - latest_price) / pos.entry_price) * 100
            pos.current_pnl_percent = pnl_percent

            if pnl_percent >= pos.profit_target:
                alert_message = f"ถึงเป้าหมายกำไร! Position ID: {pos.id}, {symbol} {timeframe}: กำไร {pnl_percent:.2f}%"
                new_alert = Alert(
                    position_id=pos.id,
                    alert_type="PROFIT_TARGET",
                    message=alert_message,
                    triggered_at=datetime.utcnow()
                )
                db.session.add(new_alert)
                pos.status = "CLOSED" # Close position when profit target is reached
            elif pnl_percent <= -pos.loss_limit:
                alert_message = f"ถึงขีดจำกัดขาดทุน! Position ID: {pos.id}, {symbol} {timeframe}: ขาดทุน {pnl_percent:.2f}%"
                new_alert = Alert(
                    position_id=pos.id,
                    alert_type="LOSS_LIMIT",
                    message=alert_message,
                    triggered_at=datetime.utcnow()
                )
                db.session.add(new_alert)
                pos.status = "CLOSED" # Close position when loss limit is reached
            db.session.commit()

        
        return jsonify({
            "prediction": int(prediction),
            "latest_price": latest_price,
            "accuracy": float(accuracy),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "timeframe": timeframe
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"เกิดข้อผิดพลาด: {str(e)}"}), 500

