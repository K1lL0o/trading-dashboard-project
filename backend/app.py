#
# 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /backend/app.py
#
import os
import requests
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    "https://killo.online",
    "https://trading-dashboard-project.vercel.app" # Your Vercel project's default URL
])

# --- GLOBAL STATE & ENVIRONMENT VARIABLES ---
live_monitor_config = {"is_running": False, "config": None}
current_trade = None
DATABASE_URL = os.getenv('DATABASE_URL')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# --- DISCORD NOTIFICATION LOGIC ---
def send_discord_notification(trade_details, reason, strategy_name):
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable not set.")
        return

    color = {"Entry": 3447003, "Take Profit": 3066993, "Stop Loss": 15158332}.get(reason, 10070709)
    title = f"🚀 New Entry: {trade_details['type']}" if reason == "Entry" else f"✅ Exit: {reason}"

    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "Symbol", "value": trade_details['symbol'], "inline": True},
            {"name": "Strategy", "value": strategy_name.replace('_', ' ').title(), "inline": True},
            {"name": "Timeframe", "value": trade_details['timeframe'], "inline": True},
            {"name": "Entry Price", "value": f"{trade_details['entry_price']:.5f}", "inline": True},
        ]
    }

    if reason != "Entry":
        pnl = trade_details['exit_price'] - trade_details['entry_price']
        if trade_details['type'] == 'SHORT': pnl = -pnl
        pnl_percent = (pnl / trade_details['entry_price']) * 100
        embed["fields"].extend([
            {"name": "Exit Price", "value": f"{trade_details['exit_price']:.5f}", "inline": True},
            {"name": "Result", "value": f"{pnl_percent:+.2f}%", "inline": True}
        ])
    else:
        embed["fields"].extend([
            {"name": "Stop Loss", "value": f"{trade_details['stop_loss']:.5f}", "inline": True},
            {"name": "Take Profit", "value": f"{trade_details['take_profit']:.5f}", "inline": True}
        ])
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print(f"Sent Discord notification for {reason}.")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

# --- ROBUST DATA CLEANING FUNCTION ---
def clean_yfinance_data(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    df.columns = [col.capitalize() for col in df.columns]
    return df

# --- CORE TRADING LOGIC ---
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
    # Add other strategies here...
    return df

# --- THE CORE WORKER LOGIC ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]:
        return

    cfg = live_monitor_config["config"]
    try:
        data = yf.download(tickers=cfg['symbol'], period='5d', interval=cfg['timeframe'], progress=False)
        if data.empty:
            print(f"Worker: No data returned for {cfg['symbol']}")
            return

        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, cfg['strategy'])
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
            atr = latest['BBU_20_2.0'] - latest['BBL_20_2.0']
            if pd.isna(atr) or atr == 0: return

            current_trade = {
                "symbol": cfg['symbol'], "type": latest['signal'], "timeframe": cfg['timeframe'],
                "entry_price": latest['Close'],
                "stop_loss": latest['Close'] - atr if latest['signal'] == 'LONG' else latest['Close'] + atr,
                "take_profit": latest['Close'] + (atr * 1.5) if latest['signal'] == 'LONG' else latest['Close'] - (atr * 1.5)
            }
            send_discord_notification(current_trade, "Entry", cfg['strategy'])

    except Exception as e:
        print(f"Error in worker thread: {e}")

# --- API TO CONTROL THE WORKER ---
@app.route('/start', methods=['POST'])
def start_monitor():
    global live_monitor_config
    config = request.json
    live_monitor_config = {"is_running": True, "config": config}
    print(f"WORKER STARTED with config: {config}")
    return jsonify({"status": "Live monitor started"})

@app.route('/stop', methods=['POST'])
def stop_monitor():
    global live_monitor_config, current_trade
    live_monitor_config = {"is_running": False, "config": None}
    current_trade = None
    print("WORKER STOPPED")
    return jsonify({"status": "Live monitor stopped"})

# --- SCHEDULER ---
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_live_trade, trigger="interval", seconds=60)
scheduler.start()

@app.route('/')
def index():
    return "<h1>Live Signal Worker is Running</h1>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)