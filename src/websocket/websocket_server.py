from flask_socketio import emit, join_room, leave_room
from flask import request
import logging
from datetime import datetime
# from src.utils.binance_websocket import get_binance_ws_client, BinanceWebSocketClient





logger = logging.getLogger(__name__)

# Store connected clients and their subscriptions
connected_clients = {}
symbol_subscriptions = {}

def init_websocket(socketio):
    """Initialize WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        client_id = request.sid if 'request' in globals() else 'unknown'
        connected_clients[client_id] = {
            'subscribed_symbols': set(),
            'connected_at': datetime.now()
        }
        logger.info(f"Client {client_id} connected")
        emit('connected', {'status': 'success', 'message': 'Connected to WebSocket server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        client_id = request.sid if 'request' in globals() else 'unknown'
        
        # Clean up subscriptions
        if client_id in connected_clients:
            subscribed_symbols = connected_clients[client_id]['subscribed_symbols']
            for symbol in subscribed_symbols:
                if symbol in symbol_subscriptions:
                    symbol_subscriptions[symbol].discard(client_id)
                    if not symbol_subscriptions[symbol]:
                        del symbol_subscriptions[symbol]
            
            del connected_clients[client_id]
        
        logger.info(f"Client {client_id} disconnected")

    @socketio.on('subscribe_symbol')
    def handle_subscribe_symbol(data):
        """Handle symbol subscription"""
        try:
            from src.utils.binance_websocket import get_binance_ws_client
            client_id = request.sid if 'request' in globals() else 'unknown'
            symbol = data.get('symbol')

            if not symbol:
                emit('error', {'message': 'Symbol is required'})
                return

            # Add client to symbol subscription
            if symbol not in symbol_subscriptions:
                symbol_subscriptions[symbol] = set()
            symbol_subscriptions[symbol].add(client_id)

            # Add symbol to client's subscriptions
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_symbols'].add(symbol)

            # Join room
            join_room(f"symbol_{symbol}")

            # ✅ Subscribe to Binance websocket
            binance_client = get_binance_ws_client(socketio)
            binance_client.subscribe_symbol(symbol)
            print(f"✅ Subscribed symbol: {symbol}")

            logger.info(f"Client {client_id} subscribed to {symbol}")
            emit('subscribed', {'symbol': symbol, 'status': 'success'})

        except Exception as e:
            logger.error(f"Error in subscribe_symbol: {str(e)}")
            emit('error', {'message': 'Failed to subscribe to symbol'})



    @socketio.on('unsubscribe_symbol')
    def handle_unsubscribe_symbol(data):
        """Handle symbol unsubscription"""
        try:
            client_id = request.sid if 'request' in globals() else 'unknown'
            symbol = data.get('symbol')
            
            if not symbol:
                emit('error', {'message': 'Symbol is required'})
                return
            
            # Remove client from symbol subscription
            if symbol in symbol_subscriptions:
                symbol_subscriptions[symbol].discard(client_id)
                if not symbol_subscriptions[symbol]:
                    del symbol_subscriptions[symbol]
            
            # Remove symbol from client's subscriptions
            if client_id in connected_clients:
                connected_clients[client_id]['subscribed_symbols'].discard(symbol)
            
            # Leave room for this symbol
            leave_room(f"symbol_{symbol}")
            
            logger.info(f"Client {client_id} unsubscribed from {symbol}")
            emit('unsubscribed', {'symbol': symbol, 'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error in unsubscribe_symbol: {str(e)}")
            emit('error', {'message': 'Failed to unsubscribe from symbol'})

    @socketio.on('get_positions')
    def handle_get_positions():
        """Handle request for current positions"""
        try:
            from src.models.trading import Position
            
            positions = Position.query.filter_by(status='open').all()
            positions_data = []
            
            for position in positions:
                positions_data.append({
                    'id': position.id,
                    'symbol': position.symbol,
                    'direction': position.direction,
                    'entry_price': float(position.entry_price),
                    'current_price': float(position.current_price) if position.current_price else float(position.entry_price),
                    'quantity': float(position.quantity),
                    'profit_target': float(position.profit_target),
                    'stop_loss': float(position.stop_loss),
                    'pnl': float(position.pnl) if position.pnl else 0.0,
                    'pnl_percentage': float(position.pnl_percentage) if position.pnl_percentage else 0.0,
                    'created_at': position.created_at.isoformat(),
                    'status': position.status
                })
            
            emit('positions_data', {'positions': positions_data})
            
        except Exception as e:
            logger.error(f"Error in get_positions: {str(e)}")
            emit('error', {'message': 'Failed to get positions'})

    @socketio.on('get_alerts')
    def handle_get_alerts():
        """Handle request for current alerts"""
        try:
            from src.models.trading import Alert
            
            alerts = Alert.query.order_by(Alert.triggered_at.desc()).limit(20).all()
            alerts_data = []
            
            for alert in alerts:
                alerts_data.append({
                    'id': alert.id,
                    'position_id': alert.position_id,
                    'alert_type': alert.alert_type,
                    'message': alert.message,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'is_read': alert.is_read
                })
            
            emit('alerts_data', {'alerts': alerts_data})
            
        except Exception as e:
            logger.error(f"Error in get_alerts: {str(e)}")
            emit('error', {'message': 'Failed to get alerts'})

def broadcast_price_update(socketio, symbol, price_data):
    """Broadcast price and candle update to subscribed clients"""
    # print(f"Broadcasting price update for {symbol}: {price_data}")
    try:
        # --- ส่งราคาปัจจุบัน ---
        price_message = {
            'type': 'price_update',
            'data': {
                'symbol': symbol,
                'price': price_data.get('price'),
                'change_24h': price_data.get('change_24h', 0),
                'timestamp': price_data.get('tick_timestamp') or price_data.get('timestamp')
            }
        }
        socketio.emit('price_update', price_message, room=f"symbol_{symbol}")

        # --- ส่งแท่งเทียน ---
        # แปลง timestamp เป็นวินาที (int)
        ts = price_data.get('timestamp')
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts)
            except ValueError:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
            ts = int(dt.timestamp())
        else:
            ts = int(ts)
        candle_message = {
            'type': 'candle_update',
            'data': {
                'symbol': symbol,
                'open': price_data.get('open'),
                'high': price_data.get('high'),
                'low': price_data.get('low'),
                'close': price_data.get('close'),
                'timestamp': ts,
                'timeframe': price_data.get('timeframe'),
            }
        }
        # print(f"Broadcasting candle update for {symbol}: {candle_message}")
        socketio.emit('candle_update', candle_message, room=f"symbol_{symbol}")

        logger.debug(f"Broadcasted price and candle update for {symbol}")

    except Exception as e:
        logger.error(f"Error broadcasting price update: {str(e)}")

def broadcast_position_update(socketio, position_data):
    """Broadcast position update to all clients"""
    try:
        message = {
            'type': 'position_update',
            'data': position_data
        }
        
        socketio.emit('position_update', message)
        logger.debug(f"Broadcasted position update for position {position_data.get('position_id')}")
        
    except Exception as e:
        logger.error(f"Error broadcasting position update: {str(e)}")

def broadcast_alert(socketio, alert_data):
    """Broadcast alert to all clients"""
    try:
        message = {
            'type': 'alert',
            'data': alert_data
        }
        
        socketio.emit('alert', message)
        logger.info(f"Broadcasted alert: {alert_data.get('alert_type')} for position {alert_data.get('position_id')}")
        
    except Exception as e:
        logger.error(f"Error broadcasting alert: {str(e)}")

def broadcast_signal_reversal(socketio, signal_data):
    """Broadcast signal reversal to all clients"""
    try:
        message = {
            'type': 'signal_reversal',
            'data': signal_data
        }
        
        socketio.emit('signal_reversal', message)
        logger.info(f"Broadcasted signal reversal for {signal_data.get('symbol')}: {signal_data.get('previous_signal')} -> {signal_data.get('new_signal')}")
        
    except Exception as e:
        logger.error(f"Error broadcasting signal reversal: {str(e)}")

def get_connected_clients_count():
    """Get the number of connected clients"""
    return len(connected_clients)

def get_symbol_subscriptions():
    """Get current symbol subscriptions"""
    return {symbol: len(clients) for symbol, clients in symbol_subscriptions.items()}


def broadcast_clear_all(socketio):
    """Broadcast event that all positions were cleared"""
    try:
        message = {
            'type': 'clear_all',
            'data': {
                'message': 'All positions cleared'
            }
        }
        socketio.emit('clear_all', message)
        logger.info("Broadcasted clear_all to all clients")
    except Exception as e:
        logger.error(f"Error broadcasting clear_all: {str(e)}")

def broadcast_clearalert_all(socketio):
    """Broadcast event that all positions were cleared"""
    try:
        message = {
            'type': 'clear_all',
            'data': {
                'message': 'All positions cleared'
            }
        }
        socketio.emit('clear_alert_all', message)
        logger.info("Broadcasted clear_all to all clients")
    except Exception as e:
        logger.error(f"Error broadcasting clear_all: {str(e)}")


# 👇 เพิ่มไว้ด้านล่างสุดของ websocket_server.py หรือจุดเหมาะสม

_binance_ws_client = None
