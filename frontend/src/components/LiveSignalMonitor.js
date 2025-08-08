import React, { useState, useEffect } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { Settings, Play, StopCircle, Zap, ZapOff } from 'lucide-react';

const LiveSignalMonitor = () => {
    const [config, setConfig] = useState({
        symbol: 'EURUSD=X',
        timeframe: '1m',
        strategy: 'momentum',
    });
    const [isRunning, setIsRunning] = useState(false);
    const [status, setStatus] = useState('Idle. Configure and start the monitor.');

    // This effect is for polling and does not need to be changed.
    useEffect(() => {
        let intervalId = null;
        if (isRunning) {
            const poll = async () => {
                try {
                    const backendUrl = process.env.REACT_APP_RENDER_WORKER_URL; // Uses the worker URL
                    if (!backendUrl) return;
                    await fetch(`${backendUrl}/check-signal`); // This endpoint is now in the worker
                } catch (error) {
                    console.error("Polling failed:", error);
                }
            };
            intervalId = setInterval(poll, 60000);
        }
        return () => clearInterval(intervalId);
    }, [isRunning]);

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
                <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center"><Settings className="w-5 h-5 mr-2 text-blue-400" />Live Signal Configuration</h2>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                            <select disabled={isRunning} value={config.symbol} onChange={(e) => setConfig({ ...config, symbol: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <optgroup label="Forex"><option value="EURUSD=X">EUR/USD</option><option value="GBPUSD=X">GBP/USD</option></optgroup>
                                <optgroup label="Crypto"><option value="BTC-USD">BTC/USD</option><option value="ETH-USD">ETH/USD</option></optgroup>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Strategy</label>
                            <select disabled={isRunning} value={config.strategy} onChange={(e) => setConfig({ ...config, strategy: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <option value="momentum">Momentum</option>
                                <option value="scalping">Scalping</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">Timeframe</label>
                            <select disabled={isRunning} value={config.timeframe} onChange={(e) => setConfig({ ...config, timeframe: e.target.value })} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white">
                                <option value="1m">1 Minute</option><option value="5m">5 Minutes</option><option value="15m">15 Minutes</option>
                            </select>
                        </div>
                        <div className="md:col-span-1 flex space-x-4">
                            {!isRunning ? (
                                <button onClick={handleStart} className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium">
                                    <Play /><span>Start Monitoring</span>
                                </button>
                            ) : (
                                <button onClick={handleStop} className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-medium">
                                    <StopCircle /><span>Stop Monitoring</span>
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </section>
            <section className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700 p-6 text-center">
                <div className="flex items-center justify-center text-xl space-x-3">
                    {isRunning ? <Zap className="text-green-400 animate-pulse" /> : <ZapOff className="text-gray-500" />}
                    <h3 className="font-semibold">Status</h3>
                </div>
                <p className="mt-2 text-gray-300">{status}</p>
            </section>
        </div>
    );
};

export default LiveSignalMonitor;