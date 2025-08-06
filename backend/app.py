# In backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)

# IMPORTANT: Configure CORS to only allow requests from your future frontend URL.
# We will add the real URL here later. For now, we allow all for testing.
CORS(app) # In production, you'd restrict this: CORS(app, origins=["https://killo.online"])

@app.route('/api/market-data')
def get_market_data():
    symbol = request.args.get('symbol', 'EURUSD=X')
    period = request.args.get('period', '3mo')
    interval = request.args.get('interval', '1h')
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval, auto_adjust=True)
        if data.empty:
            return jsonify({"error": f"No data found for symbol '{symbol}'"}), 404
        
        data.reset_index(inplace=True)
        date_col = 'Datetime' if 'Datetime' in data.columns else 'Date'
        records = data.to_dict('records')
        
        formatted_data = [
            {
                'timestamp': r[date_col].isoformat(),
                'open': r['Open'],
                'high': r['High'],
                'low': r['Low'],
                'close': r['Close'],
                'volume': r['Volume']
            } for r in records
        ]
        return jsonify(formatted_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "<h1>Your Trading Dashboard API is running!</h1>"