import React, {useState, useEffect} from 'react';
import {api} from '../../lib/api';
import {
    RefreshCw,
    AlertTriangle,
    CheckCircle,
    Info,
    Calendar,
    Filter
} from 'lucide-react';

const ActivityLogs = () => {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    const [dateRange, setDateRange] = useState({
        startDate: null,
        endDate: null
    });
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [refreshInterval, setRefreshInterval] = useState(30000);

    useEffect(() => {
        fetchLogs();
        let interval;

        if (autoRefresh) {
            interval = setInterval(fetchLogs, refreshInterval);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [filter, dateRange, autoRefresh, refreshInterval]);

    const fetchLogs = async () => {
        try {
            setIsLoading(true);
            const response = await api.getActivityLogs(
                filter,
                dateRange.startDate,
                dateRange.endDate
            );
            
            if (response?.logs) {
                setLogs(response.logs);
            } else {
                setLogs([]);
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
            setLogs([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDateChange = (type, value) => {
        setDateRange(prev => ({
            ...prev,
            [type]: value ? new Date(value) : null
        }));
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    const getLevelIcon = (level) => {
        switch (level?.toUpperCase()) {
            case 'ERROR':
                return <AlertTriangle className="w-4 h-4 text-red-400"/>;
            case 'WARNING':
                return <AlertTriangle className="w-4 h-4 text-yellow-400"/>;
            case 'INFO':
                return <Info className="w-4 h-4 text-blue-400"/>;
            default:
                return <CheckCircle className="w-4 h-4 text-green-400"/>;
        }
    };

    const getLevelStyle = (level) => {
        switch (level?.toUpperCase()) {
            case 'ERROR':
                return 'bg-red-900/50 text-red-400 ring-1 ring-red-400/50';
            case 'WARNING':
                return 'bg-yellow-900/50 text-yellow-400 ring-1 ring-yellow-400/50';
            case 'INFO':
                return 'bg-blue-900/50 text-blue-400 ring-1 ring-blue-400/50';
            default:
                return 'bg-green-900/50 text-green-400 ring-1 ring-green-400/50';
        }
    };

    return (
        <div className="space-y-8 p-6">
            {/* Controls */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-200">Activity Logs</h2>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3">
                        <label className="text-sm text-gray-400">Auto-refresh:</label>
                        <select
                            value={autoRefresh ? refreshInterval : 'off'}
                            onChange={(e) => {
                                const value = e.target.value;
                                setAutoRefresh(value !== 'off');
                                if (value !== 'off') setRefreshInterval(Number(value));
                            }}
                            className="text-sm bg-gray-800 border-gray-700 rounded-md text-gray-200 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="off">Off</option>
                            <option value="10000">10s</option>
                            <option value="30000">30s</option>
                            <option value="60000">1m</option>
                        </select>
                    </div>
                    <button
                        onClick={fetchLogs}
                        className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
                    >
                        <RefreshCw className="h-4 w-4"/>
                        Refresh
                    </button>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-gray-900 rounded-xl border border-gray-700 p-6">
                <div className="flex flex-wrap items-center gap-6">
                    <div className="flex items-center gap-3">
                        <Filter className="h-5 w-5 text-gray-400"/>
                        <select
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            className="bg-gray-800 border-gray-700 rounded-md text-gray-200 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="all">All Levels</option>
                            <option value="error">Errors</option>
                            <option value="warning">Warnings</option>
                            <option value="info">Info</option>
                        </select>
                    </div>
                    <div className="flex items-center gap-3">
                        <Calendar className="h-5 w-5 text-gray-400"/>
                        <input
                            type="date"
                            value={dateRange.startDate ? dateRange.startDate.toISOString().split('T')[0] : ''}
                            onChange={(e) => handleDateChange('startDate', e.target.value)}
                            className="bg-gray-800 border-gray-700 rounded-md text-gray-200 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <span className="text-gray-400">to</span>
                        <input
                            type="date"
                            value={dateRange.endDate ? dateRange.endDate.toISOString().split('T')[0] : ''}
                            onChange={(e) => handleDateChange('endDate', e.target.value)}
                            className="bg-gray-800 border-gray-700 rounded-md text-gray-200 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                </div>
            </div>

            {/* Logs Table */}
            <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-700">
                        <thead className="bg-gray-800">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Timestamp</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Level</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Module</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Message</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Details</th>
                        </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700 bg-gray-900">
                        {logs.map((log, index) => (
                            <tr key={log.id || index} className="hover:bg-gray-800 transition-colors duration-200">
                                <td className="px-6 py-4 text-sm text-gray-200 whitespace-nowrap">
                                    {new Date(log.timestamp).toLocaleString()}
                                </td>
                                <td className="px-6 py-4 text-sm whitespace-nowrap">
                                        <span
                                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${getLevelStyle(log.level)}`}>
                                            {getLevelIcon(log.level)}
                                            {log.level}
                                        </span>
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-200 whitespace-nowrap">
                                    {log.source || 'system'}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-200">
                                    {log.message}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-200 whitespace-nowrap">
                                    {log.user || 'System'}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-200">
                                    {log.details && (
                                        <button
                                            onClick={() => console.log(log.details)}
                                            className="text-blue-400 hover:text-blue-300 transition-colors duration-200"
                                        >
                                            View Details
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default ActivityLogs; 