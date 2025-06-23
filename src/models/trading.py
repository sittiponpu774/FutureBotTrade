from src.models.user import db
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Position(db.Model):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(5), nullable=False)
    position_type = Column(String(5), nullable=False)  # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow)
    current_price = Column(Float)
    current_pnl_percent = Column(Float)
    status = Column(String(10), default='ACTIVE')  # ACTIVE, CLOSED
    profit_target = Column(Float, default=2.0)
    loss_limit = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts = relationship('Alert', backref='position', lazy=True)

    def __repr__(self):
        return f"<Position {self.symbol}-{self.position_type}>"

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    alert_type = Column(String(20), nullable=False)  # REVERSAL, PROFIT_TARGET, LOSS_LIMIT
    message = Column(String(255), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Alert {self.alert_type} for Position {self.position_id}>"

class SignalHistory(db.Model):
    __tablename__ = 'signal_history'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(5), nullable=False)
    prediction = Column(Integer, nullable=False)  # 0=SHORT, 1=LONG
    price = Column(Float, nullable=False)
    accuracy = Column(Float)
    predicted_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Signal {self.symbol}-{self.timeframe}-{self.prediction}>"


