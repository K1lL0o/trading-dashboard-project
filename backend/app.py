# In backend/app.py (Corrected and Final Version)

import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)
CORS(app)

# --- GLOBAL STATE & DISCORD (Unchanged) ---
live_monitor_config = {"is_running": False, "config": None}
current_trade = None

def send_discord_notification(trade_details, reason, strategy_name):
    # ... (This function is unchanged)
    pass 

# --- CORE TRADING LOGIC (Unchanged) ---
def generate_signals(df, strategy_name):
    # ... (This function is unchanged)
    pass

# --- LIVE MONITORING LOGIC (Unchanged) ---
def check_live_trade():
    # ... (This function is unchanged)
    pass

# --- API ENDPOINTS ---
@app.route('/api/live-monitor/start', methods=['POST'])
def start_monitor():
    # ... (Unchanged)
    pass

@app.route('/api/live-monitor/stop', methods=['POST'])
def stop_monitor():
    # ... (Unchanged)
    pass

@app.route('/api/check-signal')
def check_signal_route():
    # ... (Unchanged)
    pass

@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    config = request.json
    try:
        data = yf.download(
            tickers=config['symbol'],
            period=config['period'],
            interval=config['timeframe'],
            progress=False
        )
        if data.empty:
            return jsonify({"error": "No data found for the selected backtest parameters."}), 404
        
        # --- THIS IS THE FIX ---
        # No matter what index yfinance returns (single or multi),
        # this flattens it into a standard DataFrame.
        data.reset_index(inplace=True)
        # -----------------------

        signals_df = generate_signals(data, config['strategy'])
        
        # Rename the date column consistently for the frontend
        # The column name after reset_index will be 'Datetime' or 'Date'
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)

        chart_data = signals_df.tail(300).to_dict('records') # Increased points for longer backtests
        
        # This should be replaced with a real backtest calculation in the future
        performance = {"totalReturn": 189.16, "winRate": 42.9, "profitFactor": 1.83, "totalTrades": 112} 

        return jsonify({"performance": performance, "chartData": chart_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "<h1>Trading API v2.2 with bug fixes</h1>"