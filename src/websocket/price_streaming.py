import time
import threading
import logging
from datetime import datetime
from src.utils.real_time_price import price_service
from src.models.trading import Position

logger = logging.getLogger(__name__)

class PriceStreamingService:
    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.running = False
        self.subscribed_symbols = set()
        self.thread = None
        
        # Initialize price service with socketio
        price_service.socketio = socketio
        
    def add_symbol(self, symbol):
        """Add symbol to streaming"""
        self.subscribed_symbols.add(symbol)
        logger.info(f"Added {symbol} to price streaming")
        
    def remove_symbol(self, symbol):
        """Remove symbol from streaming"""
        self.subscribed_symbols.discard(symbol)
        logger.info(f"Removed {symbol} from price streaming")
        
    def start(self):
        """Start price streaming service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._stream_prices, daemon=True)
            self.thread.start()
            logger.info("Price streaming service started")
            
    def stop(self):
        """Stop price streaming service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Price streaming service stopped")
        
    def _stream_prices(self):
        """Main streaming loop"""
        while self.running:
            try:
                # Get active symbols from positions
                active_symbols = self._get_active_symbols()
                
                if active_symbols:
                    # Broadcast price updates for active symbols
                    price_service.broadcast_price_updates(list(active_symbols))
                    
                # Sleep for interval
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in price streaming loop: {str(e)}")
                time.sleep(5)  # Wait longer on error
    
    def _get_active_symbols(self):
        try:
            from src.models.user import db

            with self.app.app_context():  # <- ใช้อันนี้แทน current_app
                positions = Position.query.filter_by(status='OPEN').all()
                symbols = {pos.symbol for pos in positions}
            
            symbols.update(self.subscribed_symbols)
            return symbols

        except Exception as e:
            logger.error(f"Error getting active symbols: {e}")
            return {'BTC/USDT', 'ETH/USDT', 'DOGE/USDT'}


# Global instance
price_streaming_service = None

# def get_price_streaming_service(socketio):
#     """Get or create price streaming service instance"""
#     global price_streaming_service
#     if price_streaming_service is None:
#         price_streaming_service = PriceStreamingService(socketio)
#     return price_streaming_service
def get_price_streaming_service(app, socketio):
    global price_streaming_service
    if price_streaming_service is None:
        price_streaming_service = PriceStreamingService(app, socketio)
    return price_streaming_service


