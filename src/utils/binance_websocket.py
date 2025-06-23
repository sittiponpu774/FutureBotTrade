import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import ccxt
import websocket
import json
import threading
import time
import logging
from typing import Dict, Callable, Optional
from datetime import datetime
from src.websocket.websocket_server import broadcast_price_update


logger = logging.getLogger(__name__)

def normalize_symbol(symbol: str) -> str:
    return symbol.replace("/", "").upper()

class BinanceWebSocketClient:
    """Binance WebSocket client for real-time price streaming"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.ws = None
        self.is_connected = False
        self.subscribed_symbols = set()
        self.price_callbacks = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5
        self.symbol_timeframes = {}  # <<== เพิ่มบรรทัดนี้

        # Binance WebSocket URL
        self.base_url = "wss://stream.binance.com:9443/ws/"

        
    def connect(self):
        """Connect to Binance WebSocket"""
        try:
            # Create stream URL for multiple symbols
            if self.subscribed_symbols:
                streams = [f"{symbol.lower()}@ticker" for symbol in self.subscribed_symbols]
                stream_url = self.base_url + "/".join(streams)
            else:
                # Default stream for BTCUSDT
                stream_url = self.base_url + "btcusdt@ticker"
            
            logger.info(f"Connecting to Binance WebSocket: {stream_url}")
            
            self.ws = websocket.WebSocketApp(
                stream_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance WebSocket: {e}")
            self._schedule_reconnect()
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info("Connected to Binance WebSocket")
        
        # Notify via SocketIO if available
        if self.socketio:
            self.socketio.emit('binance_status', {
                'status': 'connected',
                'message': 'Connected to Binance WebSocket',
                'timestamp': datetime.now().isoformat()
            })
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)

            # ตรวจสอบว่าเป็นอีเวนต์ ticker
            if 'e' in data and data['e'] == '24hrTicker':
                raw_symbol = data['s']  # เช่น BTCUSDT
                normalized_symbol = normalize_symbol(raw_symbol)  # เช่น BTCUSDT (กรณีมี /)

                price = float(data['c'])  # Last price
                change_24h = float(data['P'])  # 24h เปลี่ยนแปลงเป็น %
                volume = float(data['v'])  # ปริมาณ 24h

                price_data = {
                    'symbol': normalized_symbol,
                    'price': price,
                    'change_24h': change_24h,
                    'volume': volume,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'binance_ws'
                }

                # 🔁 เรียก callback ถ้ามี
                if normalized_symbol in self.price_callbacks:
                    for callback in self.price_callbacks[normalized_symbol]:
                        try:
                            callback(price_data)
                        except Exception as e:
                            logger.error(f"Error in price callback for {normalized_symbol}: {e}")

                # ✅ ส่งผ่าน SocketIO
                if self.socketio:
                    # ราคา
                    self.socketio.emit('price_update', {
                        'type': 'price_update',
                        'data': price_data
                    }, room=f"symbol_{normalized_symbol}")

                    # กราฟแท่งเทียน
                    timeframe = self.symbol_timeframes.get(normalized_symbol, "1m")
                    candle_data = get_latest_candle(normalized_symbol, timeframe)
                    self.socketio.emit('candle_update', {
                        'type': 'candle_update',
                        'data': candle_data
                    }, room=f"symbol_{normalized_symbol}")

                logger.debug(f"Price update: {normalized_symbol} = {price}")

        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"Binance WebSocket error: {error}")
        self.is_connected = False
        
        if self.socketio:
            self.socketio.emit('binance_status', {
                'status': 'error',
                'message': f'WebSocket error: {error}',
                'timestamp': datetime.now().isoformat()
            })
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.is_connected = False
        logger.warning(f"Binance WebSocket closed: {close_status_code} - {close_msg}")
        
        if self.socketio:
            self.socketio.emit('binance_status', {
                'status': 'disconnected',
                'message': 'WebSocket connection closed',
                'timestamp': datetime.now().isoformat()
            })
        
        # Schedule reconnection
        self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """Schedule reconnection attempt"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * self.reconnect_attempts
            
            logger.info(f"Scheduling reconnection attempt {self.reconnect_attempts} in {delay} seconds")
            
            def reconnect():
                time.sleep(delay)
                if not self.is_connected:
                    self.connect()
            
            reconnect_thread = threading.Thread(target=reconnect)
            reconnect_thread.daemon = True
            reconnect_thread.start()
        else:
            logger.error("Max reconnection attempts reached")
    
        # เพิ่ม self.symbol_timeframes ใน __init__
            # self.symbol_timeframes = {}  # symbol -> timeframe
    
    def subscribe_symbol(self, symbol: str, timeframe: Optional[str] = "1m", callback: Optional[Callable] = None):
        
        symbol_key = normalize_symbol(symbol)
        self.subscribed_symbols.add(symbol_key)
        self.symbol_timeframes[symbol_key] = timeframe

        # print(f"[DEBUG] subscribe_symbol called for {symbol_upper} with timeframe {timeframe}")

        if callback:
            if symbol_key not in self.price_callbacks:
                self.price_callbacks[symbol_key] = []
            self.price_callbacks[symbol_key].append(callback)

        logger.info(f"Subscribed to {symbol_key} with timeframe {timeframe}")

        # Reconnect with new subscription
        if self.is_connected:
            self.disconnect()
            time.sleep(1)
            self.connect()

    
    def unsubscribe_symbol(self, symbol: str):
        symbol_upper = symbol.upper()
        self.subscribed_symbols.discard(symbol_upper)
        
        self.price_callbacks.pop(symbol_upper, None)
        self.symbol_timeframes.pop(symbol_upper, None)  # ลบ timeframe ด้วย
        
        logger.info(f"Unsubscribed from {symbol_upper}")
        
        if self.is_connected:
            self.disconnect()
            time.sleep(1)
            self.connect()

    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_connected = False
        if self.ws:
            self.ws.close()
        logger.info("Disconnected from Binance WebSocket")
    
    def get_status(self) -> Dict:
        """Get current connection status"""
        return {
            'connected': self.is_connected,
            'subscribed_symbols': list(self.subscribed_symbols),
            'reconnect_attempts': self.reconnect_attempts,
            'timestamp': datetime.now().isoformat()
        }

# Global instance
binance_ws_client = None

def get_binance_ws_client(socketio=None):
    """Get or create Binance WebSocket client instance"""
    global binance_ws_client
    if binance_ws_client is None:
        binance_ws_client = BinanceWebSocketClient(socketio)
    return binance_ws_client

if __name__ == "__main__":
    from src.websocket.websocket_server import broadcast_price_update
    print("✅ Import OK")

def get_latest_candle(symbol, timeframe):
    exchange = ccxt.binance()
    # Binance ใช้รูปแบบ BTC/USDT
    if not "/" in symbol:
        symbol_ccxt = symbol.replace("USDT", "/USDT")
    else:
        symbol_ccxt = symbol
    ohlcv = exchange.fetch_ohlcv(symbol_ccxt, timeframe=timeframe, limit=1)
    ts, open_, high, low, close, vol = ohlcv[0]
    return {
        'symbol': symbol,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'timestamp': int(ts // 1000),
        'timeframe': timeframe,
    }