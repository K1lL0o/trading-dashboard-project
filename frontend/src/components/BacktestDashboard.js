// In frontend/src/components/BacktestDashboard.js (Updated with Dynamic Logic)

import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Settings, RefreshCw } from 'lucide-react';

// --- ADDED: Data structure to hold the valid periods for each timeframe ---
const validPeriods = {
    '1m': [
        { value: '7d', label: '7 Days (Max)' }
    ],
    '2m': [
        { value: '60d', label: '60 Days (Max)' }
    ],
    '5m': [
        { value: '60d', label: '60 Days (Max)' }
    ],
    '15m': [
        { value: '60d', label: '60 Days (Max)' }
    ],
    '30m': [
        { value: '60d', label: '60 Days (Max)' }
    ],
    '60m': [
        { value: '30d', label: '30 Days' },
        { value: '60d', label: '60 Days' },
        { value: '6mo', label: '6 Months' },
        { value: '1y', label: '1 Year' },
        { value: '2y', label: '2 Years (Max)' },
    ],
    '1d': [
        { value: '6mo', label: '6 Months' },
        { value: '1y', label: '1 Year' },
        { value: '2y', label: '2 Years' },
        { value: '5y', label: '5 Years (Max)' }
    ]
};
// --------------------------------------------------------------------------

const BacktestDashboard = () => {
    const [config, setConfig] = useState({
        symbol: 'EURUSD=X',
        timeframe: '60m', // Default to 1 hour
        period: '6mo', // Default to 6 months
        strategy: 'momentum',
    });
    const [performance, setPerformance] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // --- ADDED: Effect to ensure the selected period is always valid ---
    useEffect(() => {
        const availablePeriods = validPeriods[config.timeframe];
        const isCurrentPeriodValid = availablePeriods.some(p => p.value === config.period);

        // If the current period is not valid for the new timeframe, reset it to the first valid option.
        if (!isCurrentPeriodValid) {
            setConfig(prevConfig => ({
                ...prevConfig,
                period: availablePeriods[0].value
            }));
        }
    }, [config.timeframe]); // This hook runs ONLY when the timeframe changes
    // -------------------------------------------------------------------

    // This effect runs the backtest whenever the config is valid and changes
    useEffect(() => {
        const runBacktest = async () => {
            setLoading(true);
            setError(null);
            setPerformance(null);
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
                setChartData(data.chartData.map(d => ({ ...d, time: new Date(d.time).toLocaleDateString() })));
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        const handler = setTimeout(() => {
            runBacktest();
        }, 500); // Debounce to prevent rapid API calls

        return () => clearTimeout(handler);
    }, [config]);

    return (
        <div>
            <section className="mb-8">
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center"><Settings className="w-5 h-5 mr-2 text-blue-400" />Backtest Configuration</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                            <select value={config.symbol} onChange={(e) => setConfig({ ...config, symbol: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <optgroup label="Forex"><option value="EURUSD=X">EUR/USD</option><option value="GBPUSD=X">GBP/USD</option></optgroup>
                                <optgroup label="Crypto"><option value="BTC-USD">BTC/USD</option><option value="ETH-USD">ETH/USD</option></optgroup>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Timeframe</label>
                            {/* --- UPDATED TIMEFRAME OPTIONS --- */}
                            <select value={config.timeframe} onChange={(e) => setConfig({ ...config, timeframe: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <option value="1m">1 Minute</option>
                                <option value="5m">5 Minutes</option>
                                <option value="15m">15 Minutes</option>
                                <option value="30m">30 Minutes</option>
                                <option value="60m">1 Hour</option>
                                <option value="1d">1 Day</option>
                            </select>
                            {/* ---------------------------------- */}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Period</label>
                            {/* --- DYNAMIC PERIOD DROPDOWN --- */}
                            <select value={config.period} onChange={(e) => setConfig({ ...config, period: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                {validPeriods[config.timeframe].map(periodOption => (
                                    <option key={periodOption.value} value={periodOption.value}>
                                        {periodOption.label}
                                    </option>
                                ))}
                            </select>
                            {/* ------------------------------- */}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Strategy</label>
                            <select value={config.strategy} onChange={(e) => setConfig({ ...config, strategy: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <option value="momentum">Momentum</option>
                                <option value="scalping">Scalping</option>
                            </select>
                        </div>
                    </div>
                </div>
            </section>

            {(loading) && <div className="text-center py-8"><RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400" /></div>}
            {error && <div className="text-center py-8 text-red-400">Error: {error}</div>}

            {performance && !loading && (
                <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
                    {/* Placeholder for performance metrics */}
                </section>
            )}

            {chartData.length > 0 && !loading && (
                <section className="grid grid-cols-1 mb-8">
                    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6 min-h-[400px]">
                        <h3 className="text-lg font-semibold mb-4 text-blue-400">Backtest Results</h3>
                        <ResponsiveContainer width="100%" height={320}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                                <YAxis stroke="#9CA3AF" fontSize={12} domain={['auto', 'auto']} />
                                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} />
                                <Legend />
                                <Line dataKey="close" stroke="#3B82F6" strokeWidth={2} dot={false} name="Price" />
                                <Line dataKey="EMA_20" stroke="#F59E0B" strokeWidth={1} dot={false} name="EMA 20" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </section>
            )}
        </div>
    );
};

export default BacktestDashboard;