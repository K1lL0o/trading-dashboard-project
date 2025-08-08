#
# 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /backend/app.py
# This version is complete and fixes the SyntaxError.
#

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import traceback

app = Flask(__name__)
CORS(app, origins=["https://killo.online", "https://trading-dashboard-project.vercel.app"])

# --- GLOBAL STATE & ENVIRONMENT VARIABLES ---
live_monitor_config = {"is_running": False, "config": None}
current_trade = None
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# --- DISCORD NOTIFICATION LOGIC ---
def send_discord_notification(trade_details, reason, strategy_name):
    # This function is complete and correct
    if not DISCORD_WEBHOOK_URL: return
    color = {"Entry": 3447003, "Take Profit": 3066993, "Stop Loss": 15158332}.get(reason, 10070709)
    title = f"🚀 New Entry: {trade_details['type']}" if reason == "Entry" else f"✅ Exit: {reason}"
    embed = {"title": title, "color": color, "fields": [{"name": "Symbol", "value": trade_details['symbol'], "inline": True}, {"name": "Strategy", "value": strategy_name.replace('_', ' ').title(), "inline": True}, {"name": "Timeframe", "value": trade_details['timeframe'], "inline": True}, {"name": "Entry Price", "value": f"{trade_details['entry_price']:.5f}", "inline": True}]}
    if reason != "Entry":
        pnl = (trade_details['exit_price'] - trade_details['entry_price']) * (1 if trade_details['type'] == 'LONG' else -1)
        pnl_percent = (pnl / trade_details['entry_price']) * 100
        embed["fields"].extend([{"name": "Exit Price", "value": f"{trade_details['exit_price']:.5f}", "inline": True}, {"name": "Result", "value": f"{pnl_percent:+.2f}%", "inline": True}])
    else:
        embed["fields"].extend([{"name": "Stop Loss", "value": f"{trade_details['stop_loss']:.5f}", "inline": True}, {"name": "Take Profit", "value": f"{trade_details['take_profit']:.5f}", "inline": True}])
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
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
    # Calculate a comprehensive set of indicators
    df.ta.ema(length=5, append=True)
    df.ta.ema(length=10, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=7, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True) # Standard MACD
    df.ta.macd(fast=5, slow=12, signal=3, append=True, col_names=('MACD_5_12_3', 'MACDh_5_12_3', 'MACDs_5_12_3')) # Fast MACD
    
    df['signal'] = 'STAY_OUT'

    if strategy_name == 'momentum':
        long_conditions = (
            (df['RSI_14'] > 60) &
            (df['RSI_7'] > 65) &
            (df['EMA_5'] > df['EMA_10']) &
            (df['EMA_10'] > df['EMA_20']) &
            (df['EMA_20'] > df['EMA_50']) &
            (df['MACD_12_26_9'] > df['MACDs_12_26_9'])
        )
        short_conditions = (
            (df['RSI_14'] < 40) &
            (df['RSI_7'] < 35) &
            (df['EMA_5'] < df['EMA_10']) &
            (df['EMA_10'] < df['EMA_20']) &
            (df['EMA_20'] < df['EMA_50']) &
            (df['MACD_12_26_9'] < df['MACDs_12_26_9'])
        )
        df.loc[long_conditions, 'signal'] = 'LONG'
        df.loc[short_conditions, 'signal'] = 'SHORT'
        
    elif strategy_name == 'scalping':
        long_score = pd.Series(0, index=df.index)
        short_score = pd.Series(0, index=df.index)
        
        long_score += pd.Series((df['MACD_5_12_3'] > df['MACDs_5_12_3']) & (df['MACD_5_12_3'].shift(1) <= df['MACDs_5_12_3'].shift(1))).astype(int) * 2
        short_score += pd.Series((df['MACD_5_12_3'] < df['MACDs_5_12_3']) & (df['MACD_5_12_3'].shift(1) >= df['MACDs_5_12_3'].shift(1))).astype(int) * 2
        
        long_score += pd.Series(df['RSI_7'] < 35).astype(int)
        short_score += pd.Series(df['RSI_7'] > 65).astype(int)

        long_score += pd.Series((df['EMA_5'] > df['EMA_10']) & (df['EMA_10'] > df['EMA_20'])).astype(int)
        short_score += pd.Series((df['EMA_5'] < df['EMA_10']) & (df['EMA_10'] < df['EMA_20'])).astype(int)
        
        df.loc[long_score >= 3, 'signal'] = 'LONG'
        df.loc[short_score >= 3, 'signal'] = 'SHORT'

    return df

def run_backtest_simulation(df, initial_capital, risk_per_trade, max_trades_per_day, atr_multiplier, target_multiplier, slippage_pips, commission_per_trade):
    trades = []
    capital = initial_capital
    position = None
    daily_trade_count = {}
    slippage = slippage_pips * 0.0001
    warmup_period = 50

    for i in range(warmup_period, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Reset daily trade count
        current_date = current['time'].date()
        if current_date not in daily_trade_count:
            daily_trade_count[current_date] = 0

        # EXIT LOGIC
        if position:
            exit_reason, exit_price = None, 0.0
            if position['type'] == 'LONG':
                if current['Low'] <= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss'] - slippage
                elif current['High'] >= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit'] - slippage
            elif position['type'] == 'SHORT':
                if current['High'] >= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss'] + slippage
                elif current['Low'] <= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit'] + slippage

            if i == len(df) - 1 and not exit_reason:
                exit_reason, exit_price = "End of Period", current['Close']

            if exit_reason:
                pnl = (exit_price - position['entry_price']) * position['position_size'] if position['type'] == 'LONG' else (position['entry_price'] - exit_price) * position['position_size']
                pnl -= commission_per_trade; capital += pnl
                position.update({'exit_price': exit_price, 'pnl': pnl, 'exit_reason': exit_reason}); trades.append(position); position = None

        # ENTRY LOGIC
        if not position and current['signal'] != 'STAY_OUT' and prev['signal'] == 'STAY_OUT':
            if daily_trade_count[current_date] >= max_trades_per_day: continue

            atr = (current['BBU_20_2.0'] - current['BBL_20_2.0']) * 0.7 # Approximation of ATR
            if pd.isna(atr) or atr == 0: continue

            entry_price = current['Open'] + (slippage if current['signal'] == 'LONG' else -slippage)
            
            if current['signal'] == 'LONG':
                stop_loss = entry_price - (atr * atr_multiplier)
                take_profit = entry_price + (atr * target_multiplier)
            else: # SHORT
                stop_loss = entry_price + (atr * atr_multiplier)
                take_profit = entry_price - (atr * target_multiplier)

            risk_amount = capital * (risk_per_trade / 100)
            price_diff = abs(entry_price - stop_loss)
            position_size = risk_amount / price_diff if price_diff > 0 else 0

            if position_size > 0:
                daily_trade_count[current_date] += 1
                position = {'entry_date': current['time'], 'type': current['signal'], 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'position_size': position_size}
    if not trades: return {"error": "No trades were executed."}
    total_return = ((capital - initial_capital) / initial_capital) * 100
    wins = [t for t in trades if t['pnl'] > 0]; losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(wins) / len(trades)) * 100 if trades else 0
    total_profit = sum(t['pnl'] for t in wins); total_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999
    return {"trades": trades, "performance": {"totalReturn": round(total_return, 2), "winRate": round(win_rate, 2), "profitFactor": round(profit_factor, 2), "totalTrades": len(trades), "avgWin": round(total_profit / len(wins) if wins else 0, 2), "avgLoss": round(total_loss / len(losses) if losses else 0, 2), "maxDrawdown": round(max_drawdown * 100, 2), "finalCapital": round(capital, 2)}}

# --- THE CORE WORKER LOGIC ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]: return

    cfg = live_monitor_config["config"]
    try:
        print(f"Worker fetching data for: {cfg['symbol']}")
        ticker = yf.Ticker(cfg['symbol'])
        data = ticker.history(period='5d', interval=cfg['timeframe'], auto_adjust=True)

        if data.empty:
            print(f"Worker: yfinance returned empty DataFrame for {cfg['symbol']}.")
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
        print("--- DETAILED WORKER TRACEBACK ---")
        traceback.print_exc()
        print("---------------------------------")

# --- API ENDPOINTS (NOW ALL IN ONE PLACE) ---

# Endpoints for the Live Monitor
@app.route('/start', methods=['POST'])
def start_monitor():
    global live_monitor_config; config = request.json; live_monitor_config = {"is_running": True, "config": config}; return jsonify({"status": "Live monitor started"})

@app.route('/stop', methods=['POST'])
def stop_monitor():
    global live_monitor_config, current_trade; live_monitor_config = {"is_running": False, "config": None}; current_trade = None; return jsonify({"status": "Live monitor stopped"})

@app.route('/check-signal')
def check_signal_route():
    if live_monitor_config["is_running"]: check_live_trade(); return jsonify({"status": "checked"})

@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    config = request.get_json()
    try:
        ticker = yf.Ticker(config['symbol'])
        data = ticker.history(period=config['period'], interval=config['timeframe'], auto_adjust=True)
        if data.empty: return jsonify({"error": f"No data for '{config['symbol']}'."}), 404
        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, config['strategy'])
        date_col = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col: 'time'}, inplace=True)
        results = run_backtest_simulation(
            signals_df, 
            initial_capital=float(config.get('initialCapital', 10000)),
            risk_per_trade=float(config.get('riskPerTrade', 2.0)),
            max_trades_per_day=int(config.get('maxTradesPerDay', 5)),
            atr_multiplier=float(config.get('atrMultiplier', 1.0)),
            target_multiplier=float(config.get('targetMultiplier', 2.5)),
            slippage_pips=float(config.get('slippage', 1.5)),
            commission_per_trade=float(config.get('commission', 4.0))
        )
        if "error" in results: return jsonify(results), 400
        chart_data = signals_df.tail(300).to_dict('records')
        return jsonify({"performance": results['performance'], "trades": results['trades'], "chartData": chart_data}), 200
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": f"Backend error: {str(e)}"}), 500

# --- SCHEDULER & MAIN BLOCK ---
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_live_trade, trigger="interval", seconds=60)
scheduler.start()
@app.route('/')
def index(): return "<h1>Trading API (Live + Backtest) is Running</h1>"
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)