import threading
import time
import logging
from datetime import datetime
from src.models.trading import Position, Alert
from src.models.user import db
from src.websocket.websocket_server import broadcast_position_update, broadcast_alert

logger = logging.getLogger(__name__)

class PositionMonitoringService:
    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.running = False
        self.thread = None
        
    def start(self):
        """Start position monitoring service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_positions, daemon=True)
            self.thread.start()
            logger.info("Position monitoring service started")
            
    def stop(self):
        """Stop position monitoring service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Position monitoring service stopped")
        
    def _monitor_positions(self):
        """Main monitoring loop"""
        while self.running:
            try:
                with self.app.app_context():
                    # Get all open positions
                    positions = Position.query.filter_by(status='open').all()
                    
                    for position in positions:
                        try:
                            # Get current price (this would normally come from price streaming)
                            current_price = self._get_current_price(position.symbol)
                            
                            if current_price:
                                # Update position with current price
                                old_pnl = position.pnl or 0
                                position.current_price = current_price
                                
                                # Calculate PnL
                                if position.direction == 'LONG':
                                    pnl = (current_price - position.entry_price) * position.quantity
                                else:  # SHORT
                                    pnl = (position.entry_price - current_price) * position.quantity
                                
                                position.pnl = pnl
                                position.pnl_percentage = (pnl / (position.entry_price * position.quantity)) * 100
                                
                                # Check for alerts
                                self._check_position_alerts(position)
                                
                                # Broadcast position update if PnL changed significantly
                                if abs(pnl - old_pnl) > 0.01:  # Only broadcast if change > $0.01
                                    position_data = {
                                        'position_id': position.id,
                                        'symbol': position.symbol,
                                        'direction': position.direction,
                                        'entry_price': float(position.entry_price),
                                        'current_price': float(current_price),
                                        'quantity': float(position.quantity),
                                        'pnl': float(pnl),
                                        'pnl_percentage': float(position.pnl_percentage),
                                        'status': position.status
                                    }
                                    
                                    broadcast_position_update(self.socketio, position_data)
                                
                                db.session.commit()
                                
                        except Exception as e:
                            logger.error(f"Error monitoring position {position.id}: {str(e)}")
                            db.session.rollback()
                
                # Sleep for monitoring interval
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in position monitoring loop: {str(e)}")
                time.sleep(1)  # Wait longer on error
                
    def _get_current_price(self, symbol):
        """Get current price for symbol (placeholder)"""
        try:
            import ccxt
            exchange = ccxt.binance()
            ticker = exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None
            
    def _check_position_alerts(self, position):
        """Check if position triggers any alerts"""
        try:
            current_pnl_percentage = position.pnl_percentage or 0
            
            # Check profit target
            if current_pnl_percentage >= position.profit_target:
                self._create_alert(position, 'PROFIT_TARGET', 
                                 f"Position {position.symbol} reached profit target of {position.profit_target}%")
                
            # Check stop loss
            elif current_pnl_percentage <= -position.stop_loss:
                self._create_alert(position, 'STOP_LOSS', 
                                 f"Position {position.symbol} hit stop loss at -{position.stop_loss}%")
                
        except Exception as e:
            logger.error(f"Error checking alerts for position {position.id}: {str(e)}")
            
    def _create_alert(self, position, alert_type, message):
        """Create and broadcast alert"""
        try:
            with self.app.app_context():
            # Check if alert already exists
                existing_alert = Alert.query.filter_by(
                    position_id=position.id,
                    alert_type=alert_type
                ).first()
                
                if not existing_alert:
                    alert = Alert(
                        position_id=position.id,
                        alert_type=alert_type,
                        message=message,
                        triggered_at=datetime.now(),
                        is_read=False
                    )
                    
                    db.session.add(alert)
                    db.session.commit()
                    
                    # Broadcast alert
                    alert_data = {
                        'alert_id': alert.id,
                        'position_id': position.id,
                        'alert_type': alert_type,
                        'message': message,
                        'timestamp': alert.triggered_at.isoformat()
                    }
                    
                    broadcast_alert(self.socketio, alert_data)
                    logger.info(f"Created and broadcasted alert: {alert_type} for position {position.id}")
                
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            db.session.rollback()

# Global instance
position_monitoring_service = None

def get_position_monitoring_service(app, socketio):
    """Get or create position monitoring service instance"""
    global position_monitoring_service
    if position_monitoring_service is None:
        position_monitoring_service = PositionMonitoringService(app, socketio)
    return position_monitoring_service

