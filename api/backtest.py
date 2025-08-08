#
# 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /api/backtest.py
#
from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)

CORS(app, origins=["https://killo.online", "https://trading-dashboard-project.vercel.app"])


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
    return df

# --- ADVANCED BACKTESTING ENGINE ---
def run_backtest_simulation(df, initial_capital, slippage_pips, commission_per_trade):
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
                drawdown = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
                position['exit_price'] = exit_price
                position['pnl'] = pnl
                position['exit_reason'] = exit_reason
                trades.append(position)
                position = None

        if not position and prev['signal'] != 'STAY_OUT' and prev['signal'] != current['signal']:
            atr = prev['BBU_20_2.0'] - prev['BBL_20_2.0']
            if pd.isna(atr) or atr == 0: continue

            entry_price = current['Open'] + (slippage if prev['signal'] == 'LONG' else -slippage)
            
            if prev['signal'] == 'LONG':
                stop_loss = entry_price - atr
                take_profit = entry_price + (atr * 1.5)
            else:
                stop_loss = entry_price + atr
                take_profit = entry_price - (atr * 1.5)

            position = {'entry_date': current['time'], 'type': prev['signal'], 'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit}

    if not trades: return {"error": "No trades were executed during this backtest."}
    
    total_return_percent = ((capital - initial_capital) / initial_capital) * 100
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
    total_profit = sum(t['pnl'] for t in winning_trades)
    total_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = total_profit / total_loss if total_loss > 0 else 999
    
    return {
        "trades": trades,
        "performance": {
            "totalReturn": round(total_return_percent, 2), "winRate": round(win_rate, 2),
            "profitFactor": round(profit_factor, 2), "totalTrades": len(trades),
            "avgWin": round(total_profit / len(winning_trades) if winning_trades else 0, 2),
            "avgLoss": round(total_loss / len(losing_trades) if losing_trades else 0, 2),
            "maxDrawdown": round(max_drawdown * 100, 2), "finalCapital": round(capital, 2)
        }
    }

# --- MAIN API HANDLER ---
@app.route('/api/backtest', methods=['POST'])
def backtest_handler():
    config = request.get_json()
    try:
        data = yf.download(
            tickers=config['symbol'], period=config['period'],
            interval=config['timeframe'], progress=False
        )
        if data.empty:
            return jsonify({"error": "No data found for these parameters"}), 404
        
        clean_df = clean_yfinance_data(data)
        signals_df = generate_signals(clean_df, config['strategy'])
        
        date_col_name = 'Datetime' if 'Datetime' in signals_df.columns else 'Date'
        signals_df.rename(columns={date_col_name: 'time'}, inplace=True)
        
        results = run_backtest_simulation(
            signals_df, 10000,
            float(config.get('slippage', 1.5)), 
            float(config.get('commission', 4.0))
        )
        
        if "error" in results:
            return jsonify(results), 400

        chart_data = signals_df.tail(300).to_dict('records')

        return jsonify({
            "performance": results['performance'],
            "trades": results['trades'],
            "chartData": chart_data
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "A backend error occurred. Check server logs for details."}), 500