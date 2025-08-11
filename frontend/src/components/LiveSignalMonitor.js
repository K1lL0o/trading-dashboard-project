import { useState, useEffect, useMemo, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Filter, RefreshCw, Zap } from 'lucide-react';

const LiveSignalMonitor = () => {
    const [allTrades, setAllTrades] = useState([]);
    const [filters, setFilters] = useState({ symbol: 'ALL', timeframe: 'ALL' });
    const [loading, setLoading] = useState(true);

    const fetchTradeHistory = useCallback(async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL;
            if (!backendUrl) throw new Error("Worker URL not configured");
            const historyRes = await fetch(`${backendUrl}/api/live-signals`);
            if (!historyRes.ok) throw new Error('Failed to fetch from server');
            const historyData = await historyRes.json();
            setAllTrades(historyData);
        } catch (error) {
            toast.error(`Could not refresh trade history: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTradeHistory();
        const interval = setInterval(fetchTradeHistory, 30000); // Auto-refresh every 30 seconds
        return () => clearInterval(interval);
    }, [fetchTradeHistory]);

    // This useMemo hook filters the trades based on the dropdown selections
    const filteredTrades = useMemo(() => {
        return allTrades.filter(trade => {
            const symbolMatch = filters.symbol === 'ALL' || trade.symbol === filters.symbol;
            const timeframeMatch = filters.timeframe === 'ALL' || trade.timeframe === filters.timeframe;
            return symbolMatch && timeframeMatch;
        });
    }, [allTrades, filters]);

    // These generate the unique options for the filter dropdowns
    const uniqueSymbols = useMemo(() => ['ALL', ...Array.from(new Set(allTrades.map(t => t.symbol)))], [allTrades]);
    const uniqueTimeframes = useMemo(() => ['ALL', ...Array.from(new Set(allTrades.map(t => t.timeframe)))], [allTrades]);

    return (
        <div>
            <Toaster position="top-center" />
            <section className="mb-8">
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                    <div className="flex flex-col md:flex-row justify-between md:items-center mb-4">
                        <h2 className="text-lg font-semibold flex items-center mb-4 md:mb-0"><Zap className="w-5 h-5 mr-2 text-green-400 animate-pulse" />24/7 Live Signal Feed</h2>
                        <p className="text-sm text-gray-400">Worker is always active. Signals are logged automatically.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center"><Filter size={14} className="mr-1" /> Filter by Symbol</label>
                            <select value={filters.symbol} onChange={(e) => setFilters(f => ({ ...f, symbol: e.target.value }))} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                {uniqueSymbols.map(s => <option key={s} value={s}>{s === 'ALL' ? 'All Symbols' : s}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center"><Filter size={14} className="mr-1" /> Filter by Timeframe</label>
                            <select value={filters.timeframe} onChange={(e) => setFilters(f => ({ ...f, timeframe: e.target.value }))} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                {uniqueTimeframes.map(t => <option key={t} value={t}>{t === 'ALL' ? 'All Timeframes' : t}</option>)}
                            </select>
                        </div>
                        <button onClick={fetchTradeHistory} disabled={loading} className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-medium">
                            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            <span>{loading ? 'Refreshing...' : 'Refresh Now'}</span>
                        </button>
                    </div>
                </div>
            </section>

            <section className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-cyan-400 mb-4">Live Trade History</h3>
                <div className="overflow-x-auto max-h-[60vh]">
                    <table className="w-full">
                        <thead className="sticky top-0 bg-gray-800">
                            <tr className="border-b border-gray-600">
                                <th className="text-left py-3 px-4 text-gray-300">Entry Date</th>
                                <th className="text-left py-3 px-4 text-gray-300">Symbol</th>
                                <th className="text-left py-3 px-4 text-gray-300">Type</th>
                                <th className="text-left py-3 px-4 text-gray-300">Entry Price</th>
                                <th className="text-left py-3 px-4 text-gray-300">Exit Price</th>
                                <th className="text-left py-3 px-4 text-gray-300">Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="6" className="text-center py-8 text-gray-400">Loading trade history...</td></tr>
                            ) : filteredTrades.length > 0 ? filteredTrades.map((trade) => (
                                <tr key={trade.id} className="border-b border-gray-700/50 hover:bg-gray-700/25">
                                    <td className="py-3 px-4 text-sm">{new Date(trade.entry_date).toLocaleString()}</td>
                                    <td className="py-3 px-4 text-sm">{trade.symbol}</td>
                                    <td className="py-3 px-4">
                                        <span className={`px-2 py-1 rounded text-xs font-medium ${trade.trade_type === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                                            {trade.trade_type}
                                        </span>
                                    </td>
                                    <td className="py-3 px-4 text-sm">{trade.entry_price ? Number(trade.entry_price).toFixed(5) : 'N/A'}</td>
                                    <td className="py-3 px-4 text-sm">{trade.exit_price ? Number(trade.exit_price).toFixed(5) : <span className="text-yellow-400">Active</span>}</td>
                                    <td className="py-3 px-4 text-xs text-gray-400">{trade.exit_reason || <span className="text-yellow-400">Active</span>}</td>
                                </tr>
                            )) : (
                                <tr><td colSpan="6" className="text-center py-8 text-gray-400">No live trades have been logged yet.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
};

export default LiveSignalMonitor;