# In backend/app.py (Version 4.0 - Advanced Backtesting Engine)

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

# --- GLOBAL STATE & DISCORD (Unchanged) ---
# ... (All the live monitoring and Discord code remains the same)

# --- NEW: ADVANCED BACKTESTING ENGINE ---
def run_backtest_simulation(df, initial_capital, risk_percent, slippage_pips, commission_per_trade):
    trades = []
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0.0
    position = None
    
    # Convert slippage from pips to price
    slippage = slippage_pips * 0.0001

    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        # --- EXIT LOGIC ---
        if position:
            exit_reason = None
            exit_price = 0.0
            if position['type'] == 'LONG':
                if current['low'] <= position['stop_loss']:
                    exit_reason = "Stop Loss"
                    exit_price = position['stop_loss'] - slippage
                elif current['high'] >= position['take_profit']:
                    exit_reason = "Take Profit"
                    exit_price = position['take_profit'] - slippage
            elif position['type'] == 'SHORT':
                if current['high'] >= position['stop_loss']:
                    exit_reason = "Stop Loss"
                    exit_price = position['stop_loss'] + slippage
                elif current['low'] <= position['take_profit']:
                    exit_reason = "Take Profit"
                    exit_price = position['take_profit'] + slippage
            
            # Close position at the end of the data
            if i == len(df) - 1 and not exit_reason:
                exit_reason = "End of Period"
                exit_price = current['close']

            if exit_reason:
                # Calculate P&L
                pnl = (exit_price - position['entry_price']) if position['type'] == 'LONG' else (position['entry_price'] - exit_price)
                pnl -= commission_per_trade # Apply commission
                
                capital += pnl
                
                # Update drawdown
                peak_capital = max(peak_capital, capital)
                drawdown = (peak_capital - capital) / peak_capital
                max_drawdown = max(max_drawdown, drawdown)
                
                position['exit_price'] = exit_price
                position['pnl'] = pnl
                position['exit_reason'] = exit_reason
                trades.append(position)
                position = None

        # --- ENTRY LOGIC ---
        if not position and prev['signal'] != 'STAY_OUT' and prev['signal'] != current['signal']:
            entry_price = current['open'] + (slippage if prev['signal'] == 'LONG' else -slippage)
            
            # Use ATR from Bollinger Bands for SL/TP placement
            atr = (prev['BBU_20_2.0'] - prev['BBL_20_2.0'])
            
            if prev['signal'] == 'LONG':
                stop_loss = entry_price - atr
                take_profit = entry_price + (atr * 1.5) # Example 1.5 Reward/Risk
            else: # SHORT
                stop_loss = entry_price + atr
                take_profit = entry_price - (atr * 1.5)

            position = {
                'entry_date': current['time'],
                'type': prev['signal'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }

    # --- FINAL METRICS CALCULATION ---
    if not trades:
        return {"error": "No trades were executed during this backtest."}

    total_return_percent = ((capital - initial_capital) / initial_capital) * 100
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
    
    total_profit = sum(t['pnl'] for t in winning_trades)
    total_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999 # Avoid division by zero
    
    avg_win = total_profit / len(winning_trades) if winning_trades else 0
    avg_loss = total_loss / len(losing_trades) if losing_trades else 0

    return {
        "trades": trades,
        "performance": {
            "totalReturn": round(total_return_percent, 2),
            "winRate": round(win_rate, 2),
            "profitFactor": round(profit_factor, 2),
            "totalTrades": len(trades),
            "avgWin": round(avg_win, 2),
            "avgLoss": round(avg_loss, 2),
            "maxDrawdown": round(max_drawdown * 100, 2),
            "finalCapital": round(capital, 2)
        }
    }

# --- API ENDPOINTS ---
@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    config = request.json
    try:
        data = yf.download(
            tickers=config['symbol'], period=config['period'],
            interval=config['timeframe'], progress=False
        )
        if data.empty:
            return jsonify({"error": "No data found for the selected parameters."}), 404
        
        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, config['strategy'])
        
        # Run the full simulation
        backtest_results = run_backtest_simulation(
            signals_df,
            initial_capital=10000, # Can be made configurable later
            risk_percent=2,
            slippage_pips=float(config.get('slippage', 1.5)),
            commission_per_trade=float(config.get('commission', 4.0))
        )
        
        if "error" in backtest_results:
            return jsonify(backtest_results), 400

        # Prepare chart data for the frontend
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)
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