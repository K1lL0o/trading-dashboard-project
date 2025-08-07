import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)
CORS(app)

# --- GLOBAL STATE FOR LIVE MONITORING ---
live_monitor_config = {"is_running": False, "config": None}
current_trade = None

# --- DISCORD NOTIFICATION LOGIC ---
def send_discord_notification(trade_details, reason, strategy_name):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not set.")
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
        requests.post(webhook_url, json={"embeds": [embed]})
        print(f"Sent Discord notification for {reason}.")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

# --- CORE TRADING LOGIC (MOVED TO BACKEND) ---
def generate_signals(df, strategy_name):
    # Use pandas_ta to calculate all indicators at once
    df.ta.ema(length=5, append=True)
    df.ta.ema(length=10, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=7, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.macd(append=True)
    
    df['signal'] = 'STAY_OUT'
    
    # Example for one strategy (add more cases for others)
    if strategy_name == 'momentum':
        long_conditions = (df['RSI_14'] > 60) & (df['EMA_5'] > df['EMA_20']) & (df['EMA_20'] > df['EMA_50'])
        short_conditions = (df['RSI_14'] < 40) & (df['EMA_5'] < df['EMA_20']) & (df['EMA_20'] < df['EMA_50'])
        df.loc[long_conditions, 'signal'] = 'LONG'
        df.loc[short_conditions, 'signal'] = 'SHORT'
    
    # Add logic for 'scalping', 'mean_reversion', 'breakout' here...

    return df

def run_backtest_logic(df, capital, risk_percent):
    # This is a simplified backtest runner, similar to the frontend version
    trades = []
    position = None
    
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev_signal = df.iloc[i-1]['signal']
        
        if not position:
            if prev_signal == 'LONG' or prev_signal == 'SHORT':
                entry_price = current['open']
                atr = df['BBL_20_2.0'].iloc[i] # Simple ATR approximation
                stop_loss = entry_price - atr if prev_signal == 'LONG' else entry_price + atr
                take_profit = entry_price + (atr * 2) if prev_signal == 'LONG' else entry_price - (atr * 2)
                position = {'type': prev_signal, 'entry': entry_price, 'sl': stop_loss, 'tp': take_profit, 'entry_date': current.name}

        if position:
            exit_reason = None
            if position['type'] == 'LONG':
                if current['high'] >= position['tp']: exit_reason = 'Take Profit'
                elif current['low'] <= position['sl']: exit_reason = 'Stop Loss'
            elif position['type'] == 'SHORT':
                if current['low'] <= position['tp']: exit_reason = 'Take Profit'
                elif current['high'] >= position['sl']: exit_reason = 'Stop Loss'

            if exit_reason or i == len(df) - 1:
                exit_price = position['tp'] if exit_reason == 'Take Profit' else position['sl'] if exit_reason == 'Stop Loss' else current['close']
                pnl = (exit_price - position['entry']) if position['type'] == 'LONG' else (position['entry'] - exit_price)
                trades.append({'entry_date': position['entry_date'], 'exit_date': current.name, 'type': position['type'], 'pnl': pnl})
                capital += pnl
                position = None
    
    return {'final_capital': capital, 'trades': trades}

# --- NEW LIVE MONITORING LOGIC ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]:
        return

    cfg = live_monitor_config["config"]
    try:
        data = yf.download(tickers=cfg['symbol'], period='5d', interval=cfg['timeframe'], progress=False)
        if data.empty: return

        signals_df = generate_signals(data, cfg['strategy'])
        latest = signals_df.iloc[-1]
        prev = signals_df.iloc[-2]
        
        # EXIT LOGIC
        if current_trade:
            exit_reason = None
            if current_trade['type'] == 'LONG' and latest['close'] >= current_trade['take_profit']: exit_reason = "Take Profit"
            elif current_trade['type'] == 'LONG' and latest['close'] <= current_trade['stop_loss']: exit_reason = "Stop Loss"
            elif current_trade['type'] == 'SHORT' and latest['close'] <= current_trade['take_profit']: exit_reason = "Take Profit"
            elif current_trade['type'] == 'SHORT' and latest['close'] >= current_trade['stop_loss']: exit_reason = "Stop Loss"
            
            if exit_reason:
                current_trade['exit_price'] = latest['close']
                send_discord_notification(current_trade, exit_reason, cfg['strategy'])
                current_trade = None
            return

        # ENTRY LOGIC
        if latest['signal'] != 'STAY_OUT' and prev['signal'] == 'STAY_OUT':
            pip_value = (latest['BBU_20_2.0'] - latest['BBL_20_2.0']) # ATR from Bollinger Bands
            current_trade = {
                "symbol": cfg['symbol'], "type": latest['signal'], "timeframe": cfg['timeframe'],
                "entry_price": latest['close'],
                "stop_loss": latest['close'] - pip_value if latest['signal'] == 'LONG' else latest['close'] + pip_value,
                "take_profit": latest['close'] + (pip_value * 1.5) if latest['signal'] == 'LONG' else latest['close'] - (pip_value * 1.5)
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
    print(f"Started live monitoring with config: {config}")
    return jsonify({"status": "Live monitoring started", "config": config})

@app.route('/api/live-monitor/stop', methods=['POST'])
def stop_monitor():
    global live_monitor_config, current_trade
    live_monitor_config = {"is_running": False, "config": None}
    current_trade = None # Clear any open trades when stopping
    print("Stopped live monitoring.")
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
        
        signals_df = generate_signals(data, config['strategy'])
        # Run backtest logic (this part needs to be fully implemented)
        # For now, we'll just return the raw data and signals
        signals_df.reset_index(inplace=True)
        chart_data = signals_df.tail(200).to_dict('records')
        
        # Replace with a call to a full backtest function later
        performance = {"totalReturn": 189.16, "winRate": 42.9, "profitFactor": 1.83, "totalTrades": 112} # Placeholder

        return jsonify({"performance": performance, "chartData": chart_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "<h1>Trading API v2 with Backtesting and Live Monitoring</h1>"