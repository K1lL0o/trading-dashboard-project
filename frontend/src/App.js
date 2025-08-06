//
// 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE:  /frontend/src/App.js
// It replaces everything that Create React App put there by default.
//

import React, { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Play, Settings, TrendingUp, TrendingDown, DollarSign, Target, AlertTriangle, BarChart3, Activity, RefreshCw } from 'lucide-react';

// MODIFIED data fetching function to call the backend API via an environment variable
const fetchRealMarketData = async (symbol, period = '3mo', interval = '1h') => {
    try {
        // This is the professional way to handle API URLs.
        // Vercel will provide the value for 'REACT_APP_API_URL'.
        const backendUrl = process.env.REACT_APP_API_URL;
        if (!backendUrl) {
            throw new Error("API URL is not configured. Please set REACT_APP_API_URL environment variable.");
        }
        const apiUrl = `${backendUrl}/api/market-data?symbol=${symbol}&period=${period}&interval=${interval}`;

        const response = await fetch(apiUrl);
        const data = await response.json();

        if (!response.ok || !Array.isArray(data)) {
            const errorMessage = data.error || 'Invalid data format from backend API';
            console.error('API Error:', errorMessage);
            throw new Error(errorMessage);
        }

        // The timestamp from the backend is a string, so we convert it to a Date object.
        const marketData = data.map(item => ({
            ...item,
            timestamp: new Date(item.timestamp)
        }));

        return marketData;
    } catch (error) {
        console.error('Error fetching real market data from backend:', error);
        throw new Error(`Failed to fetch market data. Is the backend server running and configured? Error: ${error.message}`);
    }
};

// Advanced technical indicators logic (un-modified)
const calculateAdvancedIndicators = (data) => {
    if (!data || data.length < 100) return data;

    const result = [...data];

    // RSI calculation (14 and 7 periods)
    const calculateRSI = (prices, period) => {
        const gains = [];
        const losses = [];

        for (let i = 1; i < prices.length; i++) {
            const change = prices[i] - prices[i - 1];
            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? Math.abs(change) : 0);
        }

        const rsiValues = [];
        for (let i = period - 1; i < gains.length; i++) {
            const avgGain = gains.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
            const avgLoss = losses.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
            const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
            rsiValues.push(100 - (100 / (1 + rs)));
        }

        return rsiValues;
    };

    // EMA calculation
    const calculateEMA = (prices, period) => {
        const multiplier = 2 / (period + 1);
        const ema = [prices[0]];

        for (let i = 1; i < prices.length; i++) {
            ema.push((prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier)));
        }

        return ema;
    };

    // MACD calculation
    const calculateMACD = (prices, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) => {
        const fastEMA = calculateEMA(prices, fastPeriod);
        const slowEMA = calculateEMA(prices, slowPeriod);

        const macdLine = fastEMA.map((fast, i) => fast - slowEMA[i]);
        const signalLine = calculateEMA(macdLine, signalPeriod);
        const histogram = macdLine.map((macd, i) => macd - signalLine[i]);

        return { macd: macdLine, signal: signalLine, histogram };
    };

    // Bollinger Bands
    const calculateBollingerBands = (prices, period = 20, stdDev = 2) => {
        const sma = [];
        const upper = [];
        const lower = [];

        for (let i = period - 1; i < prices.length; i++) {
            const slice = prices.slice(i - period + 1, i + 1);
            const mean = slice.reduce((a, b) => a + b, 0) / period;
            const variance = slice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / period;
            const std = Math.sqrt(variance);

            sma.push(mean);
            upper.push(mean + (std * stdDev));
            lower.push(mean - (std * stdDev));
        }

        return { sma, upper, lower };
    };

    // Apply all indicators
    const closePrices = result.map(item => item.close);

    const rsi14 = calculateRSI(closePrices, 14);
    const rsi7 = calculateRSI(closePrices, 7);
    const ema5 = calculateEMA(closePrices, 5);
    const ema10 = calculateEMA(closePrices, 10);
    const ema20 = calculateEMA(closePrices, 20);
    const ema50 = calculateEMA(closePrices, 50);
    const macd = calculateMACD(closePrices);
    const fastMACD = calculateMACD(closePrices, 5, 12, 3);
    const bb = calculateBollingerBands(closePrices);

    // Apply to result array
    result.forEach((item, i) => {
        if (i >= 13 && rsi14[i - 13]) item.rsi14 = parseFloat(rsi14[i - 13].toFixed(2));
        if (i >= 6 && rsi7[i - 6]) item.rsi7 = parseFloat(rsi7[i - 6].toFixed(2));
        if (i >= 4) item.ema5 = parseFloat(ema5[i].toFixed(5));
        if (i >= 9) item.ema10 = parseFloat(ema10[i].toFixed(5));
        if (i >= 19) item.ema20 = parseFloat(ema20[i].toFixed(5));
        if (i >= 49) item.ema50 = parseFloat(ema50[i].toFixed(5));
        if (i >= 25) {
            item.macd = parseFloat(macd.macd[i].toFixed(5));
            item.macdSignal = parseFloat(macd.signal[i].toFixed(5));
            item.macdHistogram = parseFloat(macd.histogram[i].toFixed(5));
        }
        if (i >= 11) {
            item.fastMACD = parseFloat(fastMACD.macd[i].toFixed(5));
            item.fastMACDSignal = parseFloat(fastMACD.signal[i].toFixed(5));
        }
        if (i >= 19 && bb.sma[i - 19]) {
            item.bbUpper = parseFloat(bb.upper[i - 19].toFixed(5));
            item.bbLower = parseFloat(bb.lower[i - 19].toFixed(5));
            item.bbMiddle = parseFloat(bb.sma[i - 19].toFixed(5));
            item.bbWidth = parseFloat(((bb.upper[i - 19] - bb.lower[i - 19]) / bb.sma[i - 19]).toFixed(4));
        }
    });

    return result;
};

// Signal generation logic (un-modified)
const generateAdvancedSignals = (data, strategy, fundamentalSentiment = 0) => {
    if (!data || data.length < 100) return data;

    const result = [...data];

    result.forEach((item, i) => {
        if (i < 50) {
            item.signal = 'STAY_OUT';
            item.signalStrength = 0;
            item.setupType = 'None';
            return;
        }

        const prev = result[i - 1];
        let signal = 'STAY_OUT';
        let strength = 0;
        let setupType = 'None';

        if (!item.rsi14 || !item.rsi7 || !item.ema5 || !item.ema10 || !item.ema20) {
            item.signal = signal;
            item.signalStrength = strength;
            item.setupType = setupType;
            return;
        }

        switch (strategy) {
            case 'scalping':
                let longScore = 0;
                let shortScore = 0;

                if (item.fastMACD && item.fastMACDSignal && prev.fastMACD && prev.fastMACDSignal) {
                    if (item.fastMACD > item.fastMACDSignal && prev.fastMACD <= prev.fastMACDSignal) longScore += 2;
                    if (item.fastMACD < item.fastMACDSignal && prev.fastMACD >= prev.fastMACDSignal) shortScore += 2;
                }

                if (item.rsi7 < 35) longScore += 1;
                if (item.rsi7 > 65) shortScore += 1;

                if (item.ema5 > item.ema10 && item.ema10 > item.ema20) longScore += 1;
                if (item.ema5 < item.ema10 && item.ema10 < item.ema20) shortScore += 1;

                if (longScore >= 3) {
                    signal = 'LONG';
                    strength = Math.min(longScore, 5);
                    setupType = 'Scalp_Long';
                } else if (shortScore >= 3) {
                    signal = 'SHORT';
                    strength = Math.min(shortScore, 5);
                    setupType = 'Scalp_Short';
                }
                break;

            case 'momentum':
                let longConditions = 0;
                let shortConditions = 0;

                if (item.rsi14 > 60 && item.rsi7 > 65 && item.ema5 > item.ema10 && item.ema10 > item.ema20 && item.ema20 > item.ema50) {
                    longConditions += 3;
                    setupType = 'Momentum_Long';
                }
                if (item.rsi14 < 40 && item.rsi7 < 35 && item.ema5 < item.ema10 && item.ema10 < item.ema20 && item.ema20 < item.ema50) {
                    shortConditions += 3;
                    setupType = 'Momentum_Short';
                }

                if (item.macd && item.macdSignal) {
                    if (item.macd > item.macdSignal && item.macd > 0) longConditions += 1;
                    if (item.macd < item.macdSignal && item.macd < 0) shortConditions += 1;
                }

                if (longConditions >= 3) {
                    signal = 'LONG';
                    strength = longConditions;
                } else if (shortConditions >= 3) {
                    signal = 'SHORT';
                    strength = shortConditions;
                }
                break;

            case 'mean_reversion':
                if (item.bbLower && item.bbUpper && item.close <= item.bbLower && item.rsi14 < 30 && item.volume > (prev.volume * 1.1)) {
                    signal = 'LONG';
                    strength = 4;
                    setupType = 'MeanRev_Long';
                } else if (item.bbUpper && item.close >= item.bbUpper && item.rsi14 > 70 && item.volume > (prev.volume * 1.1)) {
                    signal = 'SHORT';
                    strength = 4;
                    setupType = 'MeanRev_Short';
                }
                break;

            case 'breakout':
                if (item.bbWidth && item.bbWidth < 0.02 && item.volume > (prev.volume * 1.5)) {
                    if (item.close > item.bbUpper && item.rsi14 > 50) {
                        signal = 'LONG';
                        strength = 4;
                        setupType = 'Breakout_Long';
                    } else if (item.close < item.bbLower && item.rsi14 < 50) {
                        signal = 'SHORT';
                        strength = 4;
                        setupType = 'Breakout_Short';
                    }
                }
                break;
            default:
                break;
        }

        if (signal !== 'STAY_OUT') {
            if (signal === 'LONG' && fundamentalSentiment > 0.2) strength += 1;
            else if (signal === 'SHORT' && fundamentalSentiment < -0.2) strength += 1;
            else if (signal === 'LONG' && fundamentalSentiment < -0.3) strength -= 1;
            else if (signal === 'SHORT' && fundamentalSentiment > 0.3) strength -= 1;

            if (strength <= 0) {
                signal = 'STAY_OUT';
                strength = 0;
                setupType = 'Filtered';
            }
        }

        item.signal = signal;
        item.signalStrength = strength;
        item.setupType = setupType;
    });

    return result;
};

// Backtesting logic (un-modified)
const runAdvancedBacktest = (data, config) => {
    const {
        initialCapital = 10000,
        riskPerTrade = 0.02,
        maxTradesPerDay = 5,
        atrMultiplier = 1.0,
        targetMultiplier = 2.5
    } = config;

    let capital = initialCapital;
    let position = 0;
    let entryPrice = 0;
    let stopLoss = 0;
    let takeProfit = 0;
    const trades = [];
    let currentTradeType = null;
    const dailyTradeCount = {};

    for (let i = 1; i < data.length - 1; i++) {
        const current = data[i];
        const next = data[i + 1];
        const currentDate = current.timestamp.toDateString();

        if (!dailyTradeCount[currentDate]) {
            dailyTradeCount[currentDate] = 0;
        }

        if (position === 0) {
            if (dailyTradeCount[currentDate] >= maxTradesPerDay) continue;

            if (current.signal === 'LONG' || current.signal === 'SHORT') {
                entryPrice = next.open;
                const atrApprox = (current.high - current.low) * 0.7;

                if (current.signal === 'LONG') {
                    stopLoss = entryPrice - (atrApprox * atrMultiplier);
                    takeProfit = entryPrice + (atrApprox * targetMultiplier);
                    currentTradeType = 'LONG';
                } else {
                    stopLoss = entryPrice + (atrApprox * atrMultiplier);
                    takeProfit = entryPrice - (atrApprox * targetMultiplier);
                    currentTradeType = 'SHORT';
                }

                const riskAmount = capital * riskPerTrade;
                const priceDiff = Math.abs(entryPrice - stopLoss);
                position = priceDiff > 0 ? riskAmount / priceDiff : 0;

                if (position > 0) {
                    dailyTradeCount[currentDate]++;
                    trades.push({
                        entryDate: next.timestamp, type: currentTradeType, entry: entryPrice, stopLoss, takeProfit, positionSize: position,
                        signalStrength: current.signalStrength, setupType: current.setupType, riskAmount
                    });
                }
            }
        } else {
            const { high, low } = current;
            let exitPrice = null;
            let exitReason = null;

            if (currentTradeType === 'LONG') {
                if (low <= stopLoss) { exitPrice = stopLoss; exitReason = 'Stop Loss'; }
                else if (high >= takeProfit) { exitPrice = takeProfit; exitReason = 'Take Profit'; }
            } else if (currentTradeType === 'SHORT') {
                if (high >= stopLoss) { exitPrice = stopLoss; exitReason = 'Stop Loss'; }
                else if (low <= takeProfit) { exitPrice = takeProfit; exitReason = 'Take Profit'; }
            }

            if (exitPrice) {
                const pnl = currentTradeType === 'LONG' ? (exitPrice - entryPrice) * position : (entryPrice - exitPrice) * position;
                capital += pnl;
                const lastTrade = trades[trades.length - 1];
                lastTrade.exitDate = current.timestamp;
                lastTrade.exitPrice = exitPrice;
                lastTrade.pnl = pnl;
                lastTrade.exitReason = exitReason;
                position = 0;
                currentTradeType = null;
            }
        }
    }

    if (position !== 0 && trades.length > 0) {
        const lastTrade = trades[trades.length - 1];
        const lastPrice = data[data.length - 1].close;
        const pnl = currentTradeType === 'LONG' ? (lastPrice - entryPrice) * position : (entryPrice - lastPrice) * position;
        capital += pnl;
        lastTrade.exitDate = data[data.length - 1].timestamp;
        lastTrade.exitPrice = lastPrice;
        lastTrade.pnl = pnl;
        lastTrade.exitReason = 'End of Period';
    }

    return { finalCapital: capital, trades };
};

// Performance analysis logic (un-modified)
const analyzePerformance = (initialCapital, finalCapital, trades) => {
    const completedTrades = trades.filter(t => t.pnl !== undefined);
    if (completedTrades.length === 0) return { totalReturn: 0, winRate: 0, profitFactor: 0, avgWin: 0, avgLoss: 0, maxDrawdown: 0, sharpeRatio: 0, totalTrades: 0 };

    const winningTrades = completedTrades.filter(t => t.pnl > 0);
    const losingTrades = completedTrades.filter(t => t.pnl < 0);

    const totalReturn = ((finalCapital - initialCapital) / initialCapital) * 100;
    const winRate = (winningTrades.length / completedTrades.length) * 100;

    const totalWins = winningTrades.reduce((sum, t) => sum + t.pnl, 0);
    const totalLosses = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0));
    const profitFactor = totalLosses === 0 ? Infinity : totalWins / totalLosses;

    const avgWin = winningTrades.length > 0 ? totalWins / winningTrades.length : 0;
    const avgLoss = losingTrades.length > 0 ? totalLosses / losingTrades.length : 0;

    let peak = initialCapital, maxDrawdown = 0, runningCapital = initialCapital;
    completedTrades.forEach(trade => {
        runningCapital += trade.pnl;
        if (runningCapital > peak) peak = runningCapital;
        const drawdown = ((peak - runningCapital) / peak) * 100;
        if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    });

    const returns = completedTrades.map(t => t.pnl);
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const stdDev = Math.sqrt(returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length);
    const sharpeRatio = stdDev === 0 ? 0 : avgReturn / stdDev;

    return {
        totalReturn: parseFloat(totalReturn.toFixed(2)), winRate: parseFloat(winRate.toFixed(1)), profitFactor: parseFloat(profitFactor.toFixed(2)),
        avgWin: parseFloat(avgWin.toFixed(2)), avgLoss: parseFloat(avgLoss.toFixed(2)), maxDrawdown: parseFloat(maxDrawdown.toFixed(2)),
        sharpeRatio: parseFloat(sharpeRatio.toFixed(2)), totalTrades: completedTrades.length, winningTrades: winningTrades.length, losingTrades: losingTrades.length
    };
};

// Main App Component (UI)
function TradingDashboard() {
    const [config, setConfig] = useState({
        symbol: 'EURUSD=X', timeframe: '1h', period: '3mo', strategy: 'scalping',
        initialCapital: 10000, riskPerTrade: 0.02, maxTradesPerDay: 5, fundamentalSentiment: 0.1
    });

    const [processedData, setProcessedData] = useState([]);
    const [backtest, setBacktest] = useState(null);
    const [performance, setPerformance] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const runAnalysis = async () => {
        setLoading(true);
        setError(null);
        setPerformance(null);

        try {
            const rawData = await fetchRealMarketData(config.symbol, config.period, config.timeframe);
            if (!rawData || rawData.length < 100) throw new Error('Insufficient market data. Try a different symbol or period.');

            const dataWithIndicators = calculateAdvancedIndicators(rawData);
            const dataWithSignals = generateAdvancedSignals(dataWithIndicators, config.strategy, config.fundamentalSentiment);
            setProcessedData(dataWithSignals);

            const backtestResult = runAdvancedBacktest(dataWithSignals, config);
            setBacktest(backtestResult);

            const performanceMetrics = analyzePerformance(config.initialCapital, backtestResult.finalCapital, backtestResult.trades);
            setPerformance(performanceMetrics);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const handler = setTimeout(() => {
            runAnalysis();
        }, 1000);
        return () => clearTimeout(handler);
    }, [config]);

    const chartData = useMemo(() => {
        if (!processedData.length) return [];
        return processedData.slice(-200).map(item => ({
            time: item.timestamp.toLocaleDateString(), price: item.close, ema20: item.ema20,
            bbUpper: item.bbUpper, bbLower: item.bbLower, rsi: item.rsi14
        }));
    }, [processedData]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white font-sans">
            <div className="border-b border-gray-700 bg-black/20 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <Activity className="w-8 h-8 text-blue-400" />
                            <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                                Trading Algorithm Dashboard
                            </h1>
                        </div>
                        <button onClick={runAnalysis} disabled={loading} className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-medium transition-colors">
                            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                            <span>{loading ? 'Running...' : 'Re-run'}</span>
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 flex items-center space-x-3">
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                        <span className="text-red-200">{error}</span>
                    </div>
                </div>
            )}

            <main className="max-w-7xl mx-auto px-6 py-6">
                <section className="mb-8">
                    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                        <h2 className="text-lg font-semibold mb-4 flex items-center"><Settings className="w-5 h-5 mr-2 text-blue-400" />Strategy Configuration</h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                                <select value={config.symbol} onChange={(e) => setConfig({ ...config, symbol: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500">
                                    <option value="EURUSD=X">EUR/USD</option><option value="GBPUSD=X">GBP/USD</option><option value="USDJPY=X">USD/JPY</option><option value="AUDUSD=X">AUD/USD</option><option value="USDCAD=X">USD/CAD</option><option value="BTC-USD">BTC/USD</option><option value="ETH-USD">ETH/USD</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Timeframe</label>
                                <select value={config.timeframe} onChange={(e) => setConfig({ ...config, timeframe: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500">
                                    <option value="15m">15 Min</option><option value="30m">30 Min</option><option value="1h">1 Hour</option><option value="4h">4 Hours</option><option value="1d">1 Day</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Period</label>
                                <select value={config.period} onChange={(e) => setConfig({ ...config, period: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500">
                                    <option value="1mo">1 Month</option><option value="3mo">3 Months</option><option value="6mo">6 Months</option><option value="1y">1 Year</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Strategy</label>
                                <select value={config.strategy} onChange={(e) => setConfig({ ...config, strategy: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500">
                                    <option value="scalping">Scalping</option><option value="momentum">Momentum</option><option value="mean_reversion">Mean Reversion</option><option value="breakout">Breakout</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Capital</label>
                                <input type="number" value={config.initialCapital} onChange={(e) => setConfig({ ...config, initialCapital: parseInt(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500" min="1000" step="1000" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Risk %</label>
                                <input type="number" value={config.riskPerTrade * 100} onChange={(e) => setConfig({ ...config, riskPerTrade: parseFloat(e.target.value) / 100 })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500" min="0.5" max="10" step="0.5" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Max Trades</label>
                                <input type="number" value={config.maxTradesPerDay} onChange={(e) => setConfig({ ...config, maxTradesPerDay: parseInt(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500" min="1" max="20" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">Sentiment</label>
                                <input type="number" value={config.fundamentalSentiment} onChange={(e) => setConfig({ ...config, fundamentalSentiment: parseFloat(e.target.value) })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500" min="-1" max="1" step="0.1" />
                            </div>
                        </div>
                    </div>
                </section>

                {(loading || !performance) ? (
                    <div className="flex items-center justify-center py-12"><div className="text-center"><RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-400" /><p className="text-gray-400">Running Analysis...</p></div></div>
                ) : (
                    <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
                        <div className="bg-gradient-to-br from-green-900/50 to-green-800/30 p-4 rounded-xl border border-green-500/30"><div className="flex items-center justify-between mb-2"><TrendingUp className="w-5 h-5 text-green-400" /><span className="text-xs text-green-300">RETURN</span></div><div className="text-2xl font-bold text-green-400">{performance.totalReturn > 0 ? '+' : ''}{performance.totalReturn}%</div></div>
                        <div className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 p-4 rounded-xl border border-blue-500/30"><div className="flex items-center justify-between mb-2"><Target className="w-5 h-5 text-blue-400" /><span className="text-xs text-blue-300">WIN RATE</span></div><div className="text-2xl font-bold text-blue-400">{performance.winRate}%</div></div>
                        <div className="bg-gradient-to-br from-purple-900/50 to-purple-800/30 p-4 rounded-xl border border-purple-500/30"><div className="flex items-center justify-between mb-2"><DollarSign className="w-5 h-5 text-purple-400" /><span className="text-xs text-purple-300">PROFIT FACTOR</span></div><div className="text-2xl font-bold text-purple-400">{performance.profitFactor === Infinity ? '∞' : performance.profitFactor}</div></div>
                        <div className="bg-gradient-to-br from-orange-900/50 to-orange-800/30 p-4 rounded-xl border border-orange-500/30"><div className="flex items-center justify-between mb-2"><BarChart3 className="w-5 h-5 text-orange-400" /><span className="text-xs text-orange-300">TRADES</span></div><div className="text-2xl font-bold text-orange-400">{performance.totalTrades}</div></div>
                        <div className="bg-gradient-to-br from-cyan-900/50 to-cyan-800/30 p-4 rounded-xl border border-cyan-500/30"><div className="flex items-center justify-between mb-2"><TrendingUp className="w-5 h-5 text-cyan-400" /><span className="text-xs text-cyan-300">AVG WIN</span></div><div className="text-2xl font-bold text-cyan-400">${performance.avgWin}</div></div>
                        <div className="bg-gradient-to-br from-red-900/50 to-red-800/30 p-4 rounded-xl border border-red-500/30"><div className="flex items-center justify-between mb-2"><TrendingDown className="w-5 h-5 text-red-400" /><span className="text-xs text-red-300">AVG LOSS</span></div><div className="text-2xl font-bold text-red-400">${performance.avgLoss}</div></div>
                        <div className="bg-gradient-to-br from-yellow-900/50 to-yellow-800/30 p-4 rounded-xl border border-yellow-500/30"><div className="flex items-center justify-between mb-2"><AlertTriangle className="w-5 h-5 text-yellow-400" /><span className="text-xs text-yellow-300">MAX DD</span></div><div className="text-2xl font-bold text-yellow-400">{performance.maxDrawdown}%</div></div>
                        <div className="bg-gradient-to-br from-indigo-900/50 to-indigo-800/30 p-4 rounded-xl border border-indigo-500/30"><div className="flex items-center justify-between mb-2"><Activity className="w-5 h-5 text-indigo-400" /><span className="text-xs text-indigo-300">SHARPE</span></div><div className="text-2xl font-bold text-indigo-400">{performance.sharpeRatio}</div></div>
                    </section>
                )}

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6 min-h-[400px]">
                        <h3 className="text-lg font-semibold mb-4 text-blue-400">Price & Indicators</h3>
                        {chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={320}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                                    <YAxis stroke="#9CA3AF" fontSize={12} domain={['dataMin', 'dataMax']} />
                                    <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
                                    <Legend />
                                    <Line type="monotone" dataKey="price" stroke="#3B82F6" strokeWidth={2} dot={false} name="Price" />
                                    <Line type="monotone" dataKey="ema20" stroke="#F59E0B" strokeWidth={1} dot={false} name="EMA 20" />
                                    <Line type="monotone" dataKey="bbUpper" stroke="#8B5CF6" strokeWidth={1} dot={false} strokeDasharray="5 5" name="BB Upper" />
                                    <Line type="monotone" dataKey="bbLower" stroke="#8B5CF6" strokeWidth={1} dot={false} strokeDasharray="5 5" name="BB Lower" />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : <div className="flex items-center justify-center h-full text-gray-400">Chart data is loading...</div>}
                    </div>
                    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6 min-h-[400px]">
                        <h3 className="text-lg font-semibold mb-4 text-purple-400">RSI Indicator</h3>
                        {chartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height={320}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                                    <YAxis domain={[0, 100]} stroke="#9CA3AF" fontSize={12} />
                                    <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
                                    <Legend />
                                    <Line type="monotone" dataKey="rsi" stroke="#8B5CF6" strokeWidth={2} dot={false} name="RSI" />
                                    <Line y={70} stroke="#EF4444" strokeWidth={1} strokeDasharray="3 3" name="Overbought" />
                                    <Line y={30} stroke="#10B981" strokeWidth={1} strokeDasharray="3 3" name="Oversold" />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : <div className="flex items-center justify-center h-full text-gray-400">RSI data is loading...</div>}
                    </div>
                </section>

                {backtest?.trades && backtest.trades.length > 0 && (
                    <section className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                        <h3 className="text-lg font-semibold mb-4 text-cyan-400">Recent Trades</h3>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-gray-600">
                                        <th className="text-left py-3 px-4 text-gray-300">Date</th><th className="text-left py-3 px-4 text-gray-300">Type</th><th className="text-left py-3 px-4 text-gray-300">Setup</th>
                                        <th className="text-left py-3 px-4 text-gray-300">Entry</th><th className="text-left py-3 px-4 text-gray-300">Exit</th><th className="text-right py-3 px-4 text-gray-300">P&L</th>
                                        <th className="text-left py-3 px-4 text-gray-300">Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {backtest.trades.slice(-10).reverse().map((trade, i) => (
                                        <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/25">
                                            <td className="py-3 px-4 text-sm">{trade.entryDate.toLocaleDateString()}</td>
                                            <td className="py-3 px-4"><span className={`px-2 py-1 rounded text-xs font-medium ${trade.type === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>{trade.type}</span></td>
                                            <td className="py-3 px-4 text-sm text-gray-300">{trade.setupType}</td>
                                            <td className="py-3 px-4 text-sm">{trade.entry?.toFixed(5)}</td>
                                            <td className="py-3 px-4 text-sm">{trade.exitPrice?.toFixed(5) || '-'}</td>
                                            <td className="py-3 px-4 text-right"><span className={`font-medium ${(trade.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>${(trade.pnl || 0).toFixed(2)}</span></td>
                                            <td className="py-3 px-4 text-xs text-gray-400">{trade.exitReason || 'Open'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}

export default TradingDashboard;