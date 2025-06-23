import ccxt
import random
import time
from datetime import datetime

class MockExchange:
    """Mock exchange for testing when Binance API is not available"""
    
    def __init__(self):
        self.symbols = {
            'BTC/USDT': {'price': 45000, 'change': 0},
            'ETH/USDT': {'price': 3000, 'change': 0},
            'DOGE/USDT': {'price': 0.08, 'change': 0},
            'ADA/USDT': {'price': 0.5, 'change': 0},
            'SOL/USDT': {'price': 100, 'change': 0}
        }
    
    def fetch_ticker(self, symbol):
        """Mock ticker data with realistic price movements"""
        if symbol not in self.symbols:
            raise Exception(f"Symbol {symbol} not found")
        
        # Simulate price movement
        current_data = self.symbols[symbol]
        price_change = random.uniform(-0.02, 0.02)  # ±2% change
        new_price = current_data['price'] * (1 + price_change)
        
        # Update stored price
        self.symbols[symbol]['price'] = new_price
        self.symbols[symbol]['change'] = price_change * 100
        
        return {
            'symbol': symbol,
            'last': new_price,
            'percentage': price_change * 100,
            'change': new_price - current_data['price'],
            'timestamp': int(time.time() * 1000),
            'datetime': datetime.utcnow().isoformat()
        }
    
    def fetch_ohlcv(self, symbol, timeframe='1h', limit=720):
        """Mock OHLCV data for ML training"""
        if symbol not in self.symbols:
            raise Exception(f"Symbol {symbol} not found")
        
        base_price = self.symbols[symbol]['price']
        ohlcv_data = []
        
        for i in range(limit):
            # Generate realistic OHLCV data
            timestamp = int(time.time() * 1000) - (limit - i) * 3600000  # 1 hour intervals
            
            # Random price movements
            price_variation = random.uniform(0.95, 1.05)
            open_price = base_price * price_variation
            
            high_price = open_price * random.uniform(1.0, 1.02)
            low_price = open_price * random.uniform(0.98, 1.0)
            close_price = open_price * random.uniform(0.99, 1.01)
            volume = random.uniform(1000000, 10000000)
            
            ohlcv_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
            base_price = close_price  # Use close as next base
        
        return ohlcv_data

def get_exchange(use_mock=False):
    """Get exchange instance - mock or real"""
    if use_mock:
        return MockExchange()
    else:
        try:
            exchange = ccxt.binance({
                "sandbox": False,
                "rateLimit": 1200,
                "enableRateLimit": True,
            })
            # Test connection
            exchange.fetch_ticker('BTC/USDT')
            return exchange
        except Exception as e:
            print(f"Binance API error: {e}")
            print("Falling back to mock exchange...")
            return MockExchange()

