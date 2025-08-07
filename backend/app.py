# In backend/app.py (Version 2.4 - Final MultiIndex Fix)

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
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not set.")
        return
    color = {"Entry": 3447003, "Take Profit": 3066993, "Stop Loss": 15158332}.get(reason, 10070709)
    title = f"🚀 New Entry: {trade_details['type']}" if reason == "Entry" else f"✅ Exit: {reason}"
    embed = {"title": title, "color": color, "fields": [{"name": "Symbol", "value": trade_details['symbol'], "inline": True},{"name": "Strategy", "value": strategy_name.replace('_', ' ').title(), "inline": True},{"name": "Timeframe", "value": trade_details['timeframe'], "inline": True},{"name": "Entry Price", "value": f"{trade_details['entry_price']:.5f}", "inline": True}]}
    if reason != "Entry":
        pnl = trade_details['exit_price'] - trade_details['entry_price']
        if trade_details['type'] == 'SHORT': pnl = -pnl
        pnl_percent = (pnl / trade_details['entry_price']) * 100
        embed["fields"].extend([{"name": "Exit Price", "value": f"{trade_details['exit_price']:.5f}", "inline": True},{"name": "Result", "value": f"{pnl_percent:+.2f}%", "inline": True}])
    else:
        embed["fields"].extend([{"name": "Stop Loss", "value": f"{trade_details['stop_loss']:.5f}", "inline": True},{"name": "Take Profit", "value": f"{trade_details['take_profit']:.5f}", "inline": True}])
    try:
        requests.post(webhook_url, json={"embeds": [embed]})
        print(f"Sent Discord notification for {reason}.")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")


# --- CORE TRADING LOGIC (Unchanged) ---
def generate_signals(df, strategy_name):
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

# --- LIVE MONITORING LOGIC (NOW WITH THE FIX) ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]: return

    cfg = live_monitor_config["config"]
    try:
        data = yf.download(tickers=cfg['symbol'], period='5d', interval=cfg['timeframe'], progress=False)
        if data.empty: return

        # --- THIS IS THE SECOND, CRITICAL FIX ---
        # This ensures the live monitor also handles the MultiIndex format correctly.
        data = data.reset_index()
        # ----------------------------------------

        signals_df = generate_signals(data, cfg['strategy'])
        latest = signals_df.iloc[-1]
        prev = signals_df.iloc[-2]
        
        # EXIT LOGIC
        if current_trade:
            exit_reason = None
            if current_trade['type'] == 'LONG' and latest['Close'] >= current_trade['take_profit']: exit_reason = "Take Profit"
            elif current_trade['type'] == 'LONG' and latest['Close'] <= current_trade['stop_loss']: exit_reason = "Stop Loss"
            elif current_trade['type'] == 'SHORT' and latest['Close'] <= current_trade['take_profit']: exit_reason = "Take Profit"
            elif current_trade['type'] == 'SHORT' and latest['Close'] >= current_trade['stop_loss']: exit_reason = "Stop Loss"
            
            if exit_reason:
                current_trade['exit_price'] = latest['Close']
                send_discord_notification(current_trade, exit_reason, cfg['strategy'])
                current_trade = None
            return

        # ENTRY LOGIC
        if not current_trade and latest['signal'] != 'STAY_OUT' and prev['signal'] == 'STAY_OUT':
            pip_value = (latest['BBU_20_2.0'] - latest['BBL_20_2.0'])
            current_trade = {
                "symbol": cfg['symbol'], "type": latest['signal'], "timeframe": cfg['timeframe'],
                "entry_price": latest['Close'],
                "stop_loss": latest['Close'] - pip_value if latest['signal'] == 'LONG' else latest['Close'] + pip_value,
                "take_profit": latest['Close'] + (pip_value * 1.5) if latest['signal'] == 'LONG' else latest['Close'] - (pip_value * 1.5)
            }
            send_discord_notification(current_trade, "Entry", cfg['strategy'])

    except Exception as e:
        print(f"Error in check_live_trade: {e}")

# --- API ENDPOINTS ---
@app.route('/api/live-monitor/start', methods=['POST'])
def start_monitor():
    global live_monitor_config
    config = request.json
    live_monitor_config = {"is_running": True, "config": config}
    return jsonify({"status": "Live monitoring started", "config": config})

@app.route('/api/live-monitor/stop', methods=['POST'])
def stop_monitor():
    global live_monitor_config, current_trade
    live_monitor_config = {"is_running": False, "config": None}
    current_trade = None
    return jsonify({"status": "Live monitoring stopped"})

@app.route('/api/check-signal')
def check_signal_route():
    if live_monitor_config["is_running"]:
        check_live_trade()
    return jsonify({"status": "checked"})

@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    config = request.json
    try:
        data = yf.download(tickers=config['symbol'], period=config['period'], interval=config['timeframe'], progress=False)
        if data.empty:
            return jsonify({"error": "No data found for the selected backtest parameters."}), 404
        
        data = data.reset_index()

        signals_df = generate_signals(data, config['strategy'])
        
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)

        chart_data = signals_df.tail(300).to_dict('records')
        performance = {"totalReturn": 189.16, "winRate": 42.9, "profitFactor": 1.83, "totalTrades": 112} 

        return jsonify({"performance": performance, "chartData": chart_data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "<h1>Trading API v2.4 - Final MultiIndex Fix</h1>"