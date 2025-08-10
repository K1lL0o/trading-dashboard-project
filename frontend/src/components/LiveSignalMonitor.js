import { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Settings, Play, StopCircle, Zap, ZapOff, RefreshCw } from 'lucide-react';

const LiveSignalMonitor = () => {
    const [config, setConfig] = useState({ symbol: 'EURUSD=X', timeframe: '1m', strategy: 'momentum' });
    const [isRunning, setIsRunning] = useState(false);
    const [status, setStatus] = useState('Checking monitor status...');
    const [tradeHistory, setTradeHistory] = useState([]);
    const [loading, setLoading] = useState(true);

    // Fetch initial status and trade history when component loads
    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL;
                // Fetch current monitoring status
                const statusRes = await fetch(`${backendUrl}/api/monitor-status`);
                const statusData = await statusRes.json();
                if (statusData.isRunning) {
                    setIsRunning(true);
                    setConfig(statusData.config);
                    setStatus(`Monitoring ${statusData.config.strategy} on ${statusData.config.symbol} (${statusData.config.timeframe}).`);
                } else {
                    setIsRunning(false);
                    setStatus('Idle. Configure and start the monitor.');
                }
                // Fetch trade history
                await fetchTradeHistory();
            } catch (error) {
                setStatus('Error: Could not connect to the server.');
                toast.error('Failed to fetch server status.');
            } finally {
                setLoading(false);
            }
        };
        fetchInitialData();
    }, []);

    const fetchTradeHistory = async () => {
        try {
            const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL;
            const historyRes = await fetch(`${backendUrl}/api/live-signals`);
            const historyData = await historyRes.json();
            setTradeHistory(historyData);
        } catch (error) {
            console.error("Failed to fetch trade history:", error);
        }
    };

    const handleStart = async () => {
        setStatus('Starting monitor...');
        try {
            const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL;
            const response = await fetch(`${backendUrl}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });
            if (!response.ok) throw new Error('Failed to start monitor on the server.');
            setIsRunning(true);
            setStatus(`Monitoring ${config.strategy} on ${config.symbol} (${config.timeframe}). Signals will be sent to Discord.`);
            toast.success('Live monitor started successfully!');
        } catch (error) {
            setStatus(`Error: ${error.message}`);
            toast.error('Failed to start monitor.');
        }
    };

    const handleStop = async () => {
        setStatus('Stopping monitor...');
        try {
            const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL;
            await fetch(`${backendUrl}/stop`, { method: 'POST' });
            setIsRunning(false);
            setStatus('Idle. Configure and start the monitor.');
            toast.success('Live monitor stopped.');
        } catch (error) {
            setStatus(`Error: ${error.message}`);
            toast.error('Failed to stop monitor.');
        }
    };

    return (
        <div>
            <Toaster position="top-center" />
            <section className="mb-8">
                {/* ... (Configuration UI is the same) ... */}
            </section>
            <section className="mb-8 bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6 text-center">
                {/* ... (Status UI is the same) ... */}
            </section>

            {/* --- NEW: TRADE HISTORY TABLE --- */}
            <section className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold text-cyan-400">Live Trade History</h3>
                    <button onClick={fetchTradeHistory} className="p-2 rounded-full hover:bg-gray-700"><RefreshCw size={18} /></button>
                </div>
                <div className="overflow-x-auto max-h-96">
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
                            {tradeHistory.length > 0 ? tradeHistory.map((trade) => (
                                <tr key={trade.id} className="border-b border-gray-700/50 hover:bg-gray-700/25">
                                    <td className="py-3 px-4 text-sm">{new Date(trade.entry_date).toLocaleString()}</td>
                                    <td className="py-3 px-4 text-sm">{trade.symbol}</td>
                                    <td className="py-3 px-4"><span className={`px-2 py-1 rounded text-xs font-medium ${trade.trade_type === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>{trade.trade_type}</span></td>
                                    <td className="py-3 px-4 text-sm">{trade.entry_price ? trade.entry_price.toFixed(5) : 'N/A'}</td>
                                    <td className="py-3 px-4 text-sm">{trade.exit_price ? trade.exit_price.toFixed(5) : 'Active'}</td>
                                    <td className="py-3 px-4 text-xs text-gray-400">{trade.exit_reason || 'Active'}</td>
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