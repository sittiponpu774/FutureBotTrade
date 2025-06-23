import requests
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RealTimePriceService:
    """Real-time price service with multiple sources and fallback"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.price_cache = {}
        self.last_update = {}
        
        # Price sources in order of preference
        self.price_sources = [
            ('binance', self._get_binance_price),
            ('coingecko', self._get_coingecko_price),
            ('mock', self._get_mock_price)
        ]
        
        # Symbol mapping for different APIs
        self.symbol_mapping = {
            'binance': {
                'BTC/USDT': 'BTCUSDT',
                'ETH/USDT': 'ETHUSDT', 
                'DOGE/USDT': 'DOGEUSDT',
                'ADA/USDT': 'ADAUSDT',
                'SOL/USDT': 'SOLUSDT'
            },
            'coingecko': {
                'BTC/USDT': 'bitcoin',
                'ETH/USDT': 'ethereum',
                'DOGE/USDT': 'dogecoin', 
                'ADA/USDT': 'cardano',
                'SOL/USDT': 'solana'
            }
        }
        
        # Mock prices for fallback
        self.mock_prices = {
            'BTC/USDT': 45000.0,
            'ETH/USDT': 3000.0,
            'DOGE/USDT': 0.08,
            'ADA/USDT': 0.5,
            'SOL/USDT': 100.0
        }
    
    def get_current_price(self, symbol: str) -> Tuple[Optional[float], str]:
        """Get current price from multiple sources with fallback"""
        
        # Check cache first (valid for 5 seconds)
        if symbol in self.price_cache:
            cache_time = self.last_update.get(symbol, 0)
            if time.time() - cache_time < 5:
                return self.price_cache[symbol], 'cache'
        
        # Try each price source
        for source_name, source_func in self.price_sources:
            try:
                price = source_func(symbol)
                if price:
                    # Update cache
                    self.price_cache[symbol] = price
                    self.last_update[symbol] = time.time()
                    logger.info(f"Got price for {symbol}: {price} from {source_name}")
                    return price, source_name
            except Exception as e:
                logger.warning(f"Failed to get price from {source_name}: {e}")
                continue
        
        logger.error(f"Failed to get price for {symbol} from all sources")
        return None, 'none'
    
    def _get_binance_price(self, symbol: str) -> Optional[float]:
        """Get price from Binance API"""
        binance_symbol = self.symbol_mapping['binance'].get(symbol)
        if not binance_symbol:
            return None
            
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            raise Exception(f"Binance API error: {response.status_code}")
    
    def _get_coingecko_price(self, symbol: str) -> Optional[float]:
        """Get price from CoinGecko API"""
        coingecko_id = self.symbol_mapping['coingecko'].get(symbol)
        if not coingecko_id:
            return None
            
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return float(data[coingecko_id]['usd'])
        else:
            raise Exception(f"CoinGecko API error: {response.status_code}")
    
    def _get_mock_price(self, symbol: str) -> Optional[float]:
        """Get mock price with slight random variation"""
        import random
        
        base_price = self.mock_prices.get(symbol)
        if not base_price:
            return None
        
        # Add random variation ±2%
        variation = random.uniform(-0.02, 0.02)
        price = base_price * (1 + variation)
        
        # Update mock base price slowly
        self.mock_prices[symbol] = price
        
        return round(price, 8)
    
    def get_multiple_prices(self, symbols: list) -> Dict[str, dict]:
        """Get prices for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            price, source = self.get_current_price(symbol)
            if price:
                results[symbol] = {
                    'price': price,
                    'source': source,
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def broadcast_price_updates(self, symbols: list):
        """Broadcast price updates via WebSocket"""
        if not self.socketio:
            return
            
        try:
            price_updates = self.get_multiple_prices(symbols)
            if price_updates:
                self.socketio.emit('price_update', price_updates)
                logger.info(f"Broadcasted price updates for {len(price_updates)} symbols")
        except Exception as e:
            logger.error(f"Failed to broadcast price updates: {e}")

# Global instance
price_service = RealTimePriceService()

