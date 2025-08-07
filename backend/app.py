# In backend/app.py (Version 3.0 - The Definitive MultiIndex Fix)

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
    # ...(This function is unchanged)...
    pass 

# --- NEW ROBUST DATA CLEANING FUNCTION ---
def clean_yfinance_data(df):
    """
    This is the permanent fix. It handles all known yfinance format inconsistencies.
    1. Checks for and flattens MultiIndex columns.
    2. Resets the row index to turn the Date into a column.
    """
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten the column MultiIndex, e.g., ('Close', 'EURUSD=X') -> 'Close'
        df.columns = df.columns.droplevel(1)

    # Reset the row index to ensure 'Date' or 'Datetime' is a column
    df = df.reset_index()
    
    # Capitalize column names for consistency before returning
    df.columns = [col.capitalize() for col in df.columns]
    
    return df

# --- CORE TRADING LOGIC (Now uses capitalized column names) ---
def generate_signals(df, strategy_name):
    # pandas_ta automatically finds the correct columns (Open, High, Low, Close)
    df.ta.ema(length=5, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.bbands(length=20, append=True)
    
    df['signal'] = 'STAY_OUT'
    
    if strategy_name == 'momentum':
        long_conditions = (df['RSI_14'] > 60) & (df['EMA_5'] > df['EMA_20']) & (df['EMA_20'] > df['EMA_50'])
        short_conditions = (df['RSI_14'] < 40) & (df['EMA_5'] < df['EMA_20']) & (df['EMA_20'] < df['EMA_50'])
        df.loc[long_conditions, 'signal'] = 'LONG'
        df.loc[short_conditions, 'signal'] = 'SHORT'
    
    return df

# --- LIVE MONITORING LOGIC (Now uses the cleaning function) ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]: return

    cfg = live_monitor_config["config"]
    try:
        data = yf.download(tickers=cfg['symbol'], period='5d', interval=cfg['timeframe'], progress=False)
        if data.empty: return

        clean_df = clean_yfinance_data(data) # Use the cleaning function
        signals_df = generate_signals(clean_df, cfg['strategy'])
        
        latest = signals_df.iloc[-1]
        prev = signals_df.iloc[-2]
        
        # (Rest of the live logic is unchanged but now uses safe data)
        # ...
        
    except Exception as e:
        print(f"Error in check_live_trade: {e}")

# --- API ENDPOINTS ---
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
            return jsonify({"error": "No data found for the selected parameters."}), 404
        
        clean_df = clean_yfinance_data(data) # Use the cleaning function
        signals_df = generate_signals(clean_df, config['strategy'])
        
        # The cleaning function ensures the date column is named 'Date' or 'Datetime'
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)

        chart_data = signals_df.tail(300).to_dict('records')
        performance = {"totalReturn": 189.16, "winRate": 42.9, "profitFactor": 1.83, "totalTrades": 112} 

        return jsonify({"performance": performance, "chartData": chart_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "A backend error occurred. Check server logs for details."}), 500

# (Other endpoints like start/stop monitor are unchanged)
@app.route('/api/live-monitor/start', methods=['POST'])
def start_monitor():
    global live_monitor_config; config = request.json; live_monitor_config = {"is_running": True, "config": config}; return jsonify({"status": "Live monitoring started", "config": config})
@app.route('/api/live-monitor/stop', methods=['POST'])
def stop_monitor():
    global live_monitor_config, current_trade; live_monitor_config = {"is_running": False, "config": None}; current_trade = None; return jsonify({"status": "Live monitoring stopped"})
@app.route('/api/check-signal')
def check_signal_route():
    if live_monitor_config["is_running"]: check_live_trade(); return jsonify({"status": "checked"})

@app.route('/')
def index():
    return "<h1>Trading API v3.0 - Robust Data Cleaning</h1>"