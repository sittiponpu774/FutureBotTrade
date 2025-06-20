import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from src.models.user import db
from src.routes.user import user_bp
from src.routes.predict import predict_bp
from src.routes.trading import trading_bp
from src.routes.alerts import alerts_bp
from src.models.trading import Position, Alert, SignalHistory
from src.tasks.background_tasks import start_background_tasks
from src.websocket.websocket_server import init_websocket
from src.utils.binance_websocket import get_binance_ws_client

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(predict_bp, url_prefix="/api")
app.register_blueprint(trading_bp, url_prefix="/api")
app.register_blueprint(alerts_bp, url_prefix="/api")

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all() # This will create all tables defined in db.Model subclasses

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Initialize WebSocket handlers
    init_websocket(socketio)
    
    # Initialize Binance WebSocket client
    binance_client = get_binance_ws_client(socketio)
    
    # Start background tasks
    start_background_tasks(app, socketio)
    
    # Connect to Binance WebSocket for real-time prices
    binance_client.connect()
    
    # Subscribe to common trading pairs
    common_symbols = ['BTCUSDT', 'ETHUSDT', 'DOGEUSDT', 'ADAUSDT', 'SOLUSDT']
    for symbol in common_symbols:
        binance_client.subscribe_symbol(symbol)
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
