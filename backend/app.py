# In backend/app.py
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

# --- GLOBAL STATE MANAGEMENT ---
# This dictionary will hold the state of our current trade.
# If it's None, we are looking for an entry.
# If it has data, we are in a trade and looking for an exit.
current_trade = None

def send_discord_notification(trade_details, reason):
    """Sends a formatted message to the Discord webhook."""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable not set.")
        return

    # Determine message color and title
    if reason == "Entry":
        color = 3447003  # Blue
        title = f"🚀 New Trade Entry: {trade_details['type']}"
    elif reason == "Take Profit":
        color = 3066993  # Green
        title = f"✅ Take Profit Hit: {trade_details['type']}"
    else: # Stop Loss or other exit
        color = 15158332 # Red
        title = f"❌ Stop Loss Hit: {trade_details['type']}"

    # Create the embed object for a rich message format
    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "Symbol", "value": trade_details['symbol'], "inline": True},
            {"name": "Entry Price", "value": f"{trade_details['entry_price']:.5f}", "inline": True}
        ]
    }
    
    # Add exit-specific fields
    if reason != "Entry":
        pnl = trade_details['exit_price'] - trade_details['entry_price']
        if trade_details['type'] == 'SHORT':
            pnl = -pnl
        pnl_percent = (pnl / trade_details['entry_price']) * 100
        
        embed["fields"].extend([
            {"name": "Exit Price", "value": f"{trade_details['exit_price']:.5f}", "inline": True},
            {"name": "Profit/Loss", "value": f"${pnl * 1000:.2f} ({pnl_percent:.2f}%)", "inline": False} # Example size
        ])
    else:
        embed["fields"].extend([
            {"name": "Stop Loss", "value": f"{trade_details['stop_loss']:.5f}", "inline": True},
            {"name": "Take Profit", "value": f"{trade_details['take_profit']:.5f}", "inline": True}
        ])

    # Send the request to Discord
    try:
        requests.post(webhook_url, json={"embeds": [embed]})
        print(f"Successfully sent Discord notification for {reason}.")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")


def check_and_manage_trade(df):
    """
    The main stateful logic.
    Checks for entries if not in a trade, or for exits if in a trade.
    """
    global current_trade
    
    if df.empty or len(df) < 50:
        return # Not enough data to do anything

    # --- INDICATOR CALCULATIONS ---
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    current_price = latest['close']
    
    # --- EXIT LOGIC ---
    if current_trade:
        exit_reason = None
        if current_trade['type'] == 'LONG':
            if current_price >= current_trade['take_profit']:
                exit_reason = "Take Profit"
            elif current_price <= current_trade['stop_loss']:
                exit_reason = "Stop Loss"
        elif current_trade['type'] == 'SHORT':
            if current_price <= current_trade['take_profit']:
                exit_reason = "Take Profit"
            elif current_price >= current_trade['stop_loss']:
                exit_reason = "Stop Loss"
        
        if exit_reason:
            print(f"Exit condition met: {exit_reason}")
            current_trade['exit_price'] = current_price
            send_discord_notification(current_trade, exit_reason)
            current_trade = None # CRITICAL: Reset state to look for new trades
        return

    # --- ENTRY LOGIC ---
    # Only runs if we are not currently in a trade
    entry_signal = None
    if latest['ema20'] > latest['ema50'] and previous['ema20'] <= previous['ema50']:
        entry_signal = 'LONG'
    elif latest['ema20'] < latest['ema50'] and previous['ema20'] >= previous['ema50']:
        entry_signal = 'SHORT'
        
    if entry_signal:
        print(f"Entry signal detected: {entry_signal}")
        # Define trade parameters (example: 20 pip SL/TP)
        pip_value = 0.0020
        
        current_trade = {
            "symbol": "EURUSD=X",
            "type": entry_signal,
            "entry_price": current_price,
            "stop_loss": current_price - pip_value if entry_signal == 'LONG' else current_price + pip_value,
            "take_profit": current_price + pip_value if entry_signal == 'LONG' else current_price - pip_value
        }
        send_discord_notification(current_trade, "Entry")
    return


@app.route('/api/check-signal')
def check_signal_route():
    """This is the endpoint our frontend polls. It now triggers the stateful trade manager."""
    try:
        data = yf.download(tickers='EURUSD=X', period='2d', interval='1m', progress=False)
        if not data.empty:
            data_df = data[['Close']].rename(columns={'Close': 'close'})
            check_and_manage_trade(data_df)
        # We don't need to return anything to the frontend for this.
        return jsonify({"status": "checked"})
    except Exception as e:
        print(f"Error in check_signal_route: {e}")
        return jsonify({"error": str(e)}), 500


# Your original backtesting endpoint is unchanged.
@app.route('/api/market-data')
def get_market_data():
    # ... (code for this function remains exactly the same)
    symbol = request.args.get('symbol', 'EURUSD=X')
    period = request.args.get('period', '3mo')
    interval = request.args.get('interval', '1h')
    try:
        data = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if data.empty: return jsonify({"error": f"No data found for symbol '{symbol}'"}), 404
        data.reset_index(inplace=True)
        date_col = 'Datetime' if 'Datetime' in data.columns else 'Date'
        records = data.to_dict('records')
        formatted_data = [{'timestamp': r[date_col].isoformat(),'open':r['Open'],'high':r['High'],'low':r['Low'],'close':r['Close'],'volume':r['Volume']} for r in records]
        return jsonify(formatted_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "<h1>Trading API with stateful Discord notifications is running!</h1>"