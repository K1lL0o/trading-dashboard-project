#
# 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /backend/app.py
# This is the complete, final version with the bug fix for the backtesting engine.
#

import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

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

# --- ROBUST DATA CLEANING FUNCTION ---
def clean_yfinance_data(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    # Capitalize column names for consistency
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
    # Add other strategies here if needed
    return df

# --- ADVANCED BACKTESTING ENGINE (WITH CORRECTED COLUMN NAMES) ---
def run_backtest_simulation(df, initial_capital, risk_percent, slippage_pips, commission_per_trade):
    trades = []
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0
    position = None
    slippage = slippage_pips * 0.0001
    warmup_period = 50 

    for i in range(warmup_period, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        # --- EXIT LOGIC (NOW USES CAPITALIZED COLUMN NAMES) ---
        if position:
            exit_reason = None
            exit_price = 0.0
            if position['type'] == 'LONG':
                if current['Low'] <= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss'] - slippage
                elif current['High'] >= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit'] - slippage
            elif position['type'] == 'SHORT':
                if current['High'] >= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss'] + slippage
                elif current['Low'] <= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit'] + slippage
            
            if i == len(df) - 1 and not exit_reason:
                exit_reason, exit_price = "End of Period", current['Close']

            if exit_reason:
                pnl = (exit_price - position['entry_price']) if position['type'] == 'LONG' else (position['entry_price'] - exit_price)
                pnl -= commission_per_trade
                capital += pnl
                peak_capital = max(peak_capital, capital)
                drawdown = (peak_capital - capital) / peak_capital
                max_drawdown = max(max_drawdown, drawdown)
                position['exit_price'] = exit_price
                position['pnl'] = pnl
                position['exit_reason'] = exit_reason
                trades.append(position)
                position = None

        # --- ENTRY LOGIC (NOW USES CAPITALIZED COLUMN NAMES) ---
        if not position and prev['signal'] != 'STAY_OUT' and prev['signal'] != current['signal']:
            atr = prev['BBU_20_2.0'] - prev['BBL_20_2.0']
            if pd.isna(atr) or atr == 0: continue

            entry_price = current['Open'] + (slippage if prev['signal'] == 'LONG' else -slippage)
            
            if prev['signal'] == 'LONG':
                stop_loss = entry_price - atr
                take_profit = entry_price + (atr * 1.5)
            else: # SHORT
                stop_loss = entry_price + atr
                take_profit = entry_price - (atr * 1.5)

            position = { 'entry_date': current['time'], 'type': prev['signal'], 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit }

    # --- FINAL METRICS CALCULATION ---
    if not trades: return {"error": "No trades were executed during this backtest."}
    
    total_return_percent = ((capital - initial_capital) / initial_capital) * 100
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
    total_profit = sum(t['pnl'] for t in winning_trades)
    total_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999
    avg_win = total_profit / len(winning_trades) if winning_trades else 0
    avg_loss = total_loss / len(losing_trades) if losing_trades else 0
    return { "trades": trades, "performance": { "totalReturn": round(total_return_percent, 2), "winRate": round(win_rate, 2), "profitFactor": round(profit_factor, 2), "totalTrades": len(trades), "avgWin": round(avg_win, 2), "avgLoss": round(avg_loss, 2), "maxDrawdown": round(max_drawdown * 100, 2), "finalCapital": round(capital, 2) } }

# --- LIVE MONITORING LOGIC (WITH ROBUSTNESS) ---
def check_live_trade():
    global current_trade, live_monitor_config
    if not live_monitor_config["is_running"]: return

    cfg = live_monitor_config["config"]
    try:
        data = yf.download(tickers=cfg['symbol'], period='5d', interval=cfg['timeframe'], progress=False)
        if data.empty: return

        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, cfg['strategy'])
        latest = signals_df.iloc[-1]
        prev = signals_df.iloc[-2]
        
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
        print(f"Error in check_live_trade: {e}")

# --- API ENDPOINTS ---
@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    config = request.json
    try:
        data = yf.download(tickers=config['symbol'], period=config['period'], interval=config['timeframe'], progress=False)
        if data.empty:
            return jsonify({"error": "No data found for the selected parameters."}), 404
        
        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, config['strategy'])
        
        # Rename date column for consistency before sending to backtester
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)
        
        backtest_results = run_backtest_simulation(
            signals_df,
            initial_capital=10000,
            risk_percent=2,
            slippage_pips=float(config.get('slippage', 1.5)),
            commission_per_trade=float(config.get('commission', 4.0))
        )
        
        if "error" in backtest_results:
            return jsonify(backtest_results), 400

        chart_data = signals_df.tail(300).to_dict('records')

        return jsonify({
            "performance": backtest_results['performance'],
            "trades": backtest_results['trades'],
            "chartData": chart_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "A backend error occurred. Check server logs."}), 500

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

@app.route('/')
def index():
    return "<h1>Trading API v4.2 - Final Case-Correction Fix</h1>"