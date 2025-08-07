// In frontend/src/components/BacktestDashboard.js (Final Version)

import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Settings, RefreshCw, TrendingUp, Target, DollarSign, BarChart3, TrendingDown, AlertTriangle } from 'lucide-react';

const validPeriods = { /* ... (this data structure remains unchanged) ... */ };

const BacktestDashboard = () => {
    const [config, setConfig] = useState({
        symbol: 'EURUSD=X', timeframe: '60m', period: '6mo', strategy: 'momentum',
        slippage: 1.5, // Default slippage in pips
        commission: 4.00 // Default commission in $
    });
    const [performance, setPerformance] = useState(null);
    const [trades, setTrades] = useState([]);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Effect to ensure the selected period is always valid
    useEffect(() => {
        // ... (this useEffect hook remains unchanged)
    }, [config.timeframe]);

    // Effect that runs the backtest
    useEffect(() => {
        const runBacktest = async () => {
            setLoading(true);
            setError(null);
            setPerformance(null);
            setTrades([]);
            setChartData([]);
            try {
                const backendUrl = process.env.REACT_APP_API_URL;
                const response = await fetch(`${backendUrl}/api/backtest`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Backtest failed');

                setPerformance(data.performance);
                setTrades(data.trades);
                setChartData(data.chartData.map(d => ({ ...d, time: new Date(d.time).toLocaleDateString() })));
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        const handler = setTimeout(() => { runBacktest(); }, 500);
        return () => clearTimeout(handler);
    }, [config]);

    return (
        <div>
            {/* --- CONFIGURATION SECTION (WITH NEW INPUTS) --- */}
            <section className="mb-8">
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center"><Settings className="w-5 h-5 mr-2 text-blue-400" />Backtest Configuration</h2>
                    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                        {/* ... (Symbol, Timeframe, Period, Strategy dropdowns are unchanged) ... */}
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Slippage (pips)</label>
                            <input type="number" value={config.slippage} onChange={(e) => setConfig({ ...config, slippage: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Commission ($)</label>
                            <input type="number" value={config.commission} onChange={(e) => setConfig({ ...config, commission: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white" />
                        </div>
                    </div>
                </div>
            </section>

            {(loading) && <div className="text-center py-8"><RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400" /></div>}
            {error && <div className="text-center py-8 text-red-400">Error: {error}</div>}

            {/* --- NEW: PERFORMANCE METRICS SECTION --- */}
            {performance && !loading && (
                <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
                    <StatCard icon={TrendingUp} label="Total Return" value={`${performance.totalReturn}%`} isPositive={performance.totalReturn > 0} />
                    <StatCard icon={Target} label="Win Rate" value={`${performance.winRate}%`} />
                    <StatCard icon={DollarSign} label="Profit Factor" value={performance.profitFactor} />
                    <StatCard icon={BarChart3} label="Total Trades" value={performance.totalTrades} />
                    <StatCard icon={TrendingUp} label="Avg. Win" value={`$${performance.avgWin}`} isPositive={true} />
                    <StatCard icon={TrendingDown} label="Avg. Loss" value={`$${performance.avgLoss}`} isPositive={false} />
                    <StatCard icon={AlertTriangle} label="Max Drawdown" value={`${performance.maxDrawdown}%`} isPositive={false} />
                </section>
            )}

            {/* --- Chart Section (Unchanged) --- */}
            {chartData.length > 0 && !loading && (
                <section className="grid grid-cols-1 mb-8">
                    {/* ... (The chart JSX is unchanged) ... */}
                </section>
            )}

            {/* --- NEW: TRADES TABLE SECTION --- */}
            {trades.length > 0 && !loading && (
                <section className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                    <h3 className="text-lg font-semibold mb-4 text-cyan-400">Trade Log</h3>
                    <div className="overflow-x-auto max-h-96">
                        <table className="w-full">
                            <thead className="sticky top-0 bg-gray-800">
                                <tr className="border-b border-gray-600">
                                    <th className="text-left py-3 px-4 text-gray-300">Entry Date</th>
                                    <th className="text-left py-3 px-4 text-gray-300">Type</th>
                                    <th className="text-left py-3 px-4 text-gray-300">Entry Price</th>
                                    <th className="text-left py-3 px-4 text-gray-300">Exit Price</th>
                                    <th className="text-right py-3 px-4 text-gray-300">P&L</th>
                                    <th className="text-left py-3 px-4 text-gray-300">Exit Reason</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map((trade, i) => (
                                    <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/25">
                                        <td className="py-3 px-4 text-sm">{new Date(trade.entry_date).toLocaleString()}</td>
                                        <td className="py-3 px-4"><span className={`px-2 py-1 rounded text-xs font-medium ${trade.type === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>{trade.type}</span></td>
                                        <td className="py-3 px-4 text-sm">{trade.entry_price.toFixed(5)}</td>
                                        <td className="py-3 px-4 text-sm">{trade.exit_price.toFixed(5)}</td>
                                        <td className={`py-3 px-4 text-right font-medium ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${trade.pnl.toFixed(2)}</td>
                                        <td className="py-3 px-4 text-xs text-gray-400">{trade.exit_reason}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            )}
        </div>
    );
};

// Helper component for displaying stats
const StatCard = ({ icon: Icon, label, value, isPositive }) => (
    <div className={`bg-gradient-to-br ${isPositive === true ? 'from-green-900/50' : isPositive === false ? 'from-red-900/50' : 'from-blue-900/50'} to-gray-800/30 p-4 rounded-xl border border-gray-500/30`}>
        <div className="flex items-center justify-between mb-2">
            <Icon className={`w-5 h-5 ${isPositive === true ? 'text-green-400' : isPositive === false ? 'text-red-400' : 'text-blue-400'}`} />
            <span className="text-xs text-gray-300 uppercase">{label}</span>
        </div>
        <div className={`text-2xl font-bold ${isPositive === true ? 'text-green-400' : isPositive === false ? 'text-red-400' : 'text-white'}`}>
            {value}
        </div>
    </div>
);

export default BacktestDashboard;