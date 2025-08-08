//
// 📋 PASTE THIS ENTIRE CODE BLOCK INTO THE FILE: /frontend/src/App.js
//
import React, { useState } from 'react';
import { Activity, BarChart, Clock } from 'lucide-react';
import BacktestDashboard from './components/BacktestDashboard';
import LiveSignalMonitor from './components/LiveSignalMonitor';

function App() {
    const [activeTab, setActiveTab] = useState('live');

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white font-sans">
            <header className="border-b border-gray-700 bg-black/20 backdrop-blur-sm sticky top-0 z-20">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <Activity className="w-8 h-8 text-blue-400" />
                        <h1 className="text-xl md:text-2xl font-bold">Trading Dashboard</h1>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-6">
                {/* Tab Navigation */}
                <div className="mb-6 flex space-x-2 border-b border-gray-700">
                    <button onClick={() => setActiveTab('live')} className={`flex items-center space-x-2 px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === 'live' ? 'border-blue-400 text-white' : 'border-transparent text-gray-400 hover:text-gray-200'}`}>
                        <Clock size={18} /><span>Live Signal Monitor</span>
                    </button>
                    <button onClick={() => setActiveTab('backtest')} className={`flex items-center space-x-2 px-4 py-2 font-medium border-b-2 transition-colors ${activeTab === 'backtest' ? 'border-blue-400 text-white' : 'border-transparent text-gray-400 hover:text-gray-200'}`}>
                        <BarChart size={18} /><span>Backtest Strategies</span>
                    </button>
                </div>

                {/* Content Area */}
                <div>
                    {activeTab === 'live' && <LiveSignalMonitor />}
                    {activeTab === 'backtest' && <BacktestDashboard />}
                </div>
            </main>
        </div>
    );
}

export default App;