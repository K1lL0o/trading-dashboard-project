#
# 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /backend/app.py
# This is the final, consolidated backend that handles EVERYTHING.
#

import os
import requests
import traceback
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)
CORS(app, origins=["https://killo.online", "https://trading-dashboard-project.vercel.app"])

# --- DATABASE CONNECTION & ENVIRONMENT VARIABLES ---
DATABASE_URL = os.getenv('DATABASE_URL')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TRADING_BOT_API_KEY = os.getenv('TRADING_BOT_API_KEY')

WATCHLIST = [
    # --- Forex ---
    # EUR/USD
    {"symbol": "EURUSD=X", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "EURUSD=X", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "EURUSD=X", "strategy": "momentum", "timeframe": "4h"},
    {"symbol": "EURUSD=X", "strategy": "momentum", "timeframe": "1d"},

    {"symbol": "EURUSD=X", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "EURUSD=X", "strategy": "scalping", "timeframe": "4h"},
    {"symbol": "EURUSD=X", "strategy": "scalping", "timeframe": "1d"},

    # GBP/USD
    {"symbol": "GBPUSD=X", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "GBPUSD=X", "strategy": "momentum", "timeframe": "30m"},
    {"symbol": "GBPUSD=X", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "GBPUSD=X", "strategy": "momentum", "timeframe": "4h"},
    {"symbol": "GBPUSD=X", "strategy": "momentum", "timeframe": "1d"},

    {"symbol": "GBPUSD=X", "strategy": "scalping", "timeframe": "15m"},
    {"symbol": "GBPUSD=X", "strategy": "scalping", "timeframe": "30m"},
    {"symbol": "GBPUSD=X", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "GBPUSD=X", "strategy": "scalping", "timeframe": "4h"},

    # USD/JPY
    {"symbol": "USDJPY=X", "strategy": "momentum", "timeframe": "5m"},
    {"symbol": "USDJPY=X", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "USDJPY=X", "strategy": "momentum", "timeframe": "30m"},
    {"symbol": "USDJPY=X", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "USDJPY=X", "strategy": "momentum", "timeframe": "4h"},

    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "5m"},
    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "15m"},
    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "30m"},
    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "4h"},
    {"symbol": "USDJPY=X", "strategy": "scalping", "timeframe": "1d"},

    # AUD/USD
    {"symbol": "AUDUSD=X", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "AUDUSD=X", "strategy": "momentum", "timeframe": "4h"},


    # USD/CAD
    {"symbol": "USDCAD=X", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "USDCAD=X", "strategy": "momentum", "timeframe": "30m"},
    {"symbol": "USDCAD=X", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "USDCAD=X", "strategy": "momentum", "timeframe": "4h"},

    {"symbol": "USDCAD=X", "strategy": "scalping", "timeframe": "15m"},
    {"symbol": "USDCAD=X", "strategy": "scalping", "timeframe": "30m"},
    {"symbol": "USDCAD=X", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "USDCAD=X", "strategy": "scalping", "timeframe": "4h"},
    {"symbol": "USDCAD=X", "strategy": "scalping", "timeframe": "1d"},

    # --- Crypto ---
    # BTC/USD
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "5m"},
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "30m"},
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "4h"},
    {"symbol": "BTC-USD", "strategy": "momentum", "timeframe": "1d"},

    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "5m"},
    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "15m"},
    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "30m"},
    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "4h"},
    {"symbol": "BTC-USD", "strategy": "scalping", "timeframe": "1d"},

    # ETH/USD
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "5m"},
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "15m"},
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "30m"},
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "60m"},
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "4h"},
    {"symbol": "ETH-USD", "strategy": "momentum", "timeframe": "1d"},

    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "5m"},
    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "15m"},
    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "30m"},
    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "60m"},
    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "4h"},
    {"symbol": "ETH-USD", "strategy": "scalping", "timeframe": "1d"},
]


def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# --- DISCORD NOTIFICATION LOGIC ---
def send_discord_notification(trade_details, reason, strategy_name):
    if not DISCORD_WEBHOOK_URL: return
    color = {"Entry": 3447003, "Take Profit": 3066993, "Stop Loss": 15158332}.get(reason, 10070709)
    title = f"🚀 New Entry: {trade_details['type']}" if reason == "Entry" else f"✅ Exit: {reason}"
    embed = {"title": title,"color": color,"fields": [{"name": "Symbol","value": trade_details['symbol'],"inline": True},{"name": "Strategy","value": strategy_name.replace('_', ' ').title(),"inline": True},{"name": "Timeframe","value": trade_details['timeframe'],"inline": True},{"name": "Entry Price","value": f"{trade_details['entry_price']:.5f}","inline": True}]}
    if reason != "Entry":
        pnl = (trade_details['exit_price'] - trade_details['entry_price']) * (1 if trade_details['type'] == 'LONG' else -1)
        pnl_percent = (pnl / trade_details['entry_price']) * 100 if trade_details['entry_price'] != 0 else 0
        embed["fields"].extend([{"name": "Exit Price", "value": f"{trade_details['exit_price']:.5f}", "inline": True}, {"name": "Result", "value": f"{pnl_percent:+.2f}%", "inline": True}])
    else:
        embed["fields"].extend([{"name": "Stop Loss", "value": f"{trade_details['stop_loss']:.5f}", "inline": True}, {"name": "Take Profit", "value": f"{trade_details['take_profit']:.5f}", "inline": True}])
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

# --- ROBUST DATA CLEANING FUNCTION ---
def clean_yfinance_data(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
    df = df.reset_index()
    df.columns = [col.lower() for col in df.columns] # Standardize to lowercase
    return df

def generate_signals(df, strategy_name):
    df.ta.ema(length=5, append=True, close='close'); df.ta.ema(length=10, append=True, close='close'); df.ta.ema(length=20, append=True, close='close'); df.ta.ema(length=50, append=True, close='close')
    df.ta.rsi(length=7, append=True, close='close'); df.ta.rsi(length=14, append=True, close='close'); df.ta.bbands(length=20, append=True, close='close')
    df.ta.macd(fast=12, slow=26, signal=9, append=True, close='close')
    df.ta.macd(fast=5, slow=12, signal=3, append=True, col_names=('macd_5_12_3', 'macdh_5_12_3', 'macds_5_12_3'), close='close')
    df.columns = [col.lower() for col in df.columns]
    df['signal'] = 'STAY_OUT'
    if strategy_name == 'momentum':
        long_conditions = ((df['rsi_14'] > 60) & (df['rsi_7'] > 65) & (df['ema_5'] > df['ema_10']) & (df['ema_10'] > df['ema_20']) & (df['ema_20'] > df['ema_50']) & (df['macd_12_26_9'] > df['macds_12_26_9']))
        short_conditions = ((df['rsi_14'] < 40) & (df['rsi_7'] < 35) & (df['ema_5'] < df['ema_10']) & (df['ema_10'] < df['ema_20']) & (df['ema_20'] < df['ema_50']) & (df['macd_12_26_9'] < df['macds_12_26_9']))
        df.loc[long_conditions, 'signal'] = 'LONG'; df.loc[short_conditions, 'signal'] = 'SHORT'
    elif strategy_name == 'scalping':
        long_score = pd.Series(0, index=df.index); short_score = pd.Series(0, index=df.index)
        long_score += pd.Series((df['macd_5_12_3'] > df['macds_5_12_3']) & (df['macd_5_12_3'].shift(1) <= df['macds_5_12_3'].shift(1))).astype(int) * 2
        short_score += pd.Series((df['macd_5_12_3'] < df['macds_5_12_3']) & (df['macd_5_12_3'].shift(1) >= df['macds_5_12_3'].shift(1))).astype(int) * 2
        long_score += pd.Series(df['rsi_7'] < 35).astype(int); short_score += pd.Series(df['rsi_7'] > 65).astype(int)
        long_score += pd.Series((df['ema_5'] > df['ema_10']) & (df['ema_10'] > df['ema_20'])).astype(int)
        short_score += pd.Series((df['ema_5'] < df['ema_10']) & (df['ema_10'] < df['ema_20'])).astype(int)
        df.loc[long_score >= 3, 'signal'] = 'LONG'; df.loc[short_score >= 3, 'signal'] = 'SHORT'
    return df

# --- ADVANCED BACKTESTING ENGINE (WITH CORRECTED LOWERCASE COLUMN NAMES) ---
def run_backtest_simulation(df, initial_capital, risk_per_trade, max_trades_per_day, atr_multiplier, target_multiplier, slippage_pips, commission_per_trade):
    trades, capital, peak_capital, max_drawdown, position, daily_trade_count, slippage, warmup_period = [], initial_capital, initial_capital, 0.0, None, {}, slippage_pips * 0.0001, 50
    equity_curve = []
    for i in range(warmup_period, len(df)):
        current, prev = df.iloc[i], df.iloc[i-1]
        current_date = current['time'].date()
        if current_date not in daily_trade_count: daily_trade_count[current_date] = 0
        equity_curve.append({'time': current['time'], 'capital': capital})
        if position:
            exit_reason, exit_price = None, 0.0
            if position['type'] == 'LONG':
                if current['low'] <= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss']
                elif current['high'] >= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit']
            elif position['type'] == 'SHORT':
                if current['high'] >= position['stop_loss']: exit_reason, exit_price = "Stop Loss", position['stop_loss']
                elif current['low'] <= position['take_profit']: exit_reason, exit_price = "Take Profit", position['take_profit']
            if i == len(df) - 1 and not exit_reason: exit_reason, exit_price = "End of Period", current['close']
            if exit_reason:
                exit_price += (slippage if position['type'] == 'SHORT' else -slippage)
                pnl = (exit_price - position['entry_price']) * position['position_size'] if position['type'] == 'LONG' else (position['entry_price'] - exit_price) * position['position_size']
                pnl -= commission_per_trade; capital += pnl; peak_capital = max(peak_capital, capital)
                drawdown = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
                position.update({'exit_price': exit_price, 'pnl': pnl, 'exit_reason': exit_reason}); trades.append(position); position = None
        if not position and prev['signal'] == 'STAY_OUT' and current['signal'] != 'STAY_OUT':
            if daily_trade_count[current_date] >= max_trades_per_day: continue
            atr_approx = (current['high'] - current['low']) * 0.7
            if pd.isna(atr_approx) or atr_approx == 0: continue
            entry_price = current['open'] + (slippage if current['signal'] == 'LONG' else -slippage)
            if current['signal'] == 'LONG':
                stop_loss = entry_price - (atr_approx * atr_multiplier)
                take_profit = entry_price + (atr_approx * target_multiplier)
            else:
                stop_loss = entry_price + (atr_approx * atr_multiplier)
                take_profit = entry_price - (atr_approx * target_multiplier)
            risk_amount = capital * (risk_per_trade / 100); price_diff = abs(entry_price - stop_loss)
            position_size = risk_amount / price_diff if price_diff > 0 else 0
            if position_size > 0:
                daily_trade_count[current_date] += 1
                position = {'entry_date': current['time'], 'type': current['signal'], 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit, 'position_size': position_size}
    if not trades: return {"trades": [], "performance": {"totalReturn": 0, "winRate": 0, "profitFactor": 0, "totalTrades": 0, "avgWin": 0, "avgLoss": 0, "maxDrawdown": 0, "finalCapital": initial_capital}, "error": "No trades were executed."}
    total_return = ((capital - initial_capital) / initial_capital) * 100
    wins = [t for t in trades if t['pnl'] > 0]; losses = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(wins) / len(trades)) * 100 if trades else 0; total_profit = sum(t['pnl'] for t in wins); total_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999
    return {"trades": trades, "performance": {"totalReturn": round(total_return, 2), "winRate": round(win_rate, 2), "profitFactor": round(profit_factor, 2), "totalTrades": len(trades), "avgWin": round(total_profit/len(wins) if wins else 0, 2), "avgLoss": round(total_loss/len(losses) if losses else 0, 2), "maxDrawdown": round(max_drawdown*100, 2), "finalCapital": round(capital, 2)}, "equityCurve": equity_curve}

# --- WATCHLIST WORKER LOGIC (WITH CORRECTED LOWERCASE COLUMN NAMES) ---
def check_all_signals():
    print(f"--- Worker running. Checking {len(WATCHLIST)} configurations. ---")
    for config in WATCHLIST:
        try: process_single_config(config)
        except Exception as e: print(f"--- ERROR processing config {config} ---"); traceback.print_exc()

def process_single_config(cfg):
    conn = get_db_connection()
    if not conn: return
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, trade_type, entry_price, stop_loss, take_profit FROM live_signals WHERE status = 'active' AND symbol = %s AND strategy = %s AND timeframe = %s ORDER BY entry_date DESC LIMIT 1;", (cfg['symbol'], cfg['strategy'], cfg['timeframe']))
        active_trade_row = cur.fetchone()
        data = yf.Ticker(cfg['symbol']).history(period='5d', interval=cfg['timeframe'], auto_adjust=True)
        if data.empty: return
        clean_df = clean_yfinance_data(data); signals_df = generate_signals(clean_df, cfg['strategy'])
        latest, prev = signals_df.iloc[-1], signals_df.iloc[-2]
        if active_trade_row:
            trade_id, trade_type, entry_price, stop_loss, take_profit = active_trade_row
            exit_reason, exit_price = None, None
            if trade_type == 'LONG' and latest['close'] >= take_profit: exit_reason, exit_price = "Take Profit", latest['close']
            elif trade_type == 'LONG' and latest['close'] <= stop_loss: exit_reason, exit_price = "Stop Loss", latest['close']
            elif trade_type == 'SHORT' and latest['close'] <= take_profit: exit_reason, exit_price = "Take Profit", latest['close']
            elif trade_type == 'SHORT' and latest['close'] >= stop_loss: exit_reason, exit_price = "Stop Loss", latest['close']
            if exit_reason:
                cur.execute("UPDATE live_signals SET status = 'closed', exit_price = %s, exit_date = NOW(), exit_reason = %s WHERE id = %s;", (exit_price, exit_reason, trade_id)); conn.commit()
                send_discord_notification({"symbol": cfg['symbol'], "type": trade_type, "timeframe": cfg['timeframe'], "entry_price": entry_price, "exit_price": exit_price}, exit_reason, cfg['strategy'])
        elif not active_trade_row and prev['signal'] == 'STAY_OUT' and latest['signal'] != 'STAY_OUT':
            atr = latest['bbu_20_2.0'] - latest['bbl_20_2.0']
            if pd.isna(atr) or atr == 0: return
            entry_price = latest['close']; stop_loss = entry_price - atr if latest['signal'] == 'LONG' else entry_price + atr; take_profit = entry_price + (atr * 1.5) if latest['signal'] == 'LONG' else entry_price - (atr * 1.5)
            trade = {"symbol": cfg['symbol'], "type": latest['signal'], "timeframe": cfg['timeframe'], "entry_price": entry_price, "stop_loss": stop_loss, "take_profit": take_profit}
            cur.execute("INSERT INTO live_signals (symbol, strategy, timeframe, status, trade_type, entry_price, stop_loss, take_profit, entry_date) VALUES (%s, %s, %s, 'active', %s, %s, %s, %s, NOW());", (cfg['symbol'], cfg['strategy'], cfg['timeframe'], latest['signal'], entry_price, stop_loss, take_profit)); conn.commit()
            send_discord_notification(trade, "Entry", cfg['strategy'])
    except Exception as e:
        traceback.print_exc()
    finally:
        if conn: cur.close(); conn.close()

# --- API ENDPOINTS ---
@app.route('/api/live-signals', methods=['GET'])
def get_live_signals():
    # (This function is unchanged and correct)
    conn = get_db_connection(); signals = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, symbol, strategy, timeframe, status, trade_type, entry_price, exit_price, stop_loss, take_profit, entry_date, exit_date, exit_reason FROM live_signals ORDER BY entry_date DESC LIMIT 100;")
        signals_data = cur.fetchall()
        if cur.description is not None:
            columns = [desc[0] for desc in cur.description]
            signals = [dict(zip(columns, row)) for row in signals_data]
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500
    finally:
        if conn: cur.close(); conn.close()
    return jsonify(signals)

@app.route('/api/backtest', methods=['POST'])
def backtest_route():
    # (This function is unchanged and correct)
    config = request.get_json()
    try:
        ticker = yf.Ticker(config['symbol'])
        data = ticker.history(period=config['period'], interval=config['timeframe'], auto_adjust=True)
        if data.empty: return jsonify({"error": f"No data for '{config['symbol']}'."}), 404
        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, config['strategy'])
        date_col = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col: 'time'}, inplace=True)
        results = run_backtest_simulation(signals_df, float(config.get('initialCapital', 10000)), float(config.get('riskPerTrade', 2.0)), int(config.get('maxTradesPerDay', 5)), float(config.get('atrMultiplier', 1.0)), float(config.get('targetMultiplier', 2.5)), float(config.get('slippage', 1.5)), float(config.get('commission', 4.0)))
        if "error" in results: return jsonify({ "performance": results.get('performance'), "trades": [], "chartData": [], "error": results['error'] }), 200
        chart_data = signals_df.tail(300).to_dict('records')
        return jsonify({"performance": results['performance'], "trades": results['trades'],"equityCurve": results['equityCurve'], "chartData": chart_data}), 200
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": f"Backend error: {str(e)}"}), 500

@app.route('/api/get-latest-signal', methods=['GET'])
def get_latest_signal():
    provided_key = request.headers.get('X-API-KEY')
    if not provided_key or provided_key != TRADING_BOT_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    signal = None
    cur = conn.cursor() # Define cursor here
    try:
        cur.execute("""
            SELECT symbol, strategy, timeframe, trade_type, entry_price, stop_loss, take_profit, entry_date
            FROM live_signals 
            WHERE status = 'active' AND entry_date >= NOW() - INTERVAL '2 minutes'
            ORDER BY entry_date DESC 
            LIMIT 1;
        """)
        trade_data = cur.fetchone()
        if trade_data:
            columns = [desc[0] for desc in cur.description]
            signal = dict(zip(columns, trade_data))
            if signal and 'entry_date' in signal:
                signal['entry_date'] = signal['entry_date'].isoformat()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    # --- THIS IS THE CRITICAL FIX ---
    # The 'finally' block MUST come after the 'try/except' and before the final 'return'.
    finally:
        if cur: cur.close()
        if conn: conn.close()
    # ---------------------------------
        
    return jsonify(signal)

# --- SCHEDULER & MAIN BLOCK ---
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_all_signals, trigger="interval", seconds=60)
scheduler.start()
@app.route('/')
def index(): return "<h1>24/7 Watchlist Worker is Running</h1>"
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
