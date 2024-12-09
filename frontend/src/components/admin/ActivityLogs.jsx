import React, {useState, useEffect} from 'react';
import {api} from '../../lib/api';

const ActivityLogs = () => {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [filter, setFilter] = useState('all');

    useEffect(() => {
        fetchLogs();
    }, [filter]);

    const fetchLogs = async () => {
        try {
            setIsLoading(true);
            const response = await api.getActivityLogs();
            if (response?.logs) {
                const filteredLogs = filter === 'all'
                    ? response.logs
                    : response.logs.filter(log => log.level.toLowerCase() === filter);
                setLogs(filteredLogs);
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

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="flex gap-4">
                <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
                >
                    <option value="all">All Logs</option>
                    <option value="error">Errors</option>
                    <option value="warning">Warnings</option>
                    <option value="info">Info</option>
                </select>
            </div>

            {/* Logs Table */}
            <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                <table className="w-full">
                    <thead>
                    <tr className="bg-gray-50 dark:bg-gray-800">
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Timestamp</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Level</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">Message</th>
                        <th className="px-6 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-400">User</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {logs.map(log => (
                        <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                            <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                {new Date(log.timestamp).toLocaleString()}
                            </td>
                            <td className="px-6 py-4 text-sm">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                                    ${log.level === 'ERROR' ? 'bg-red-100 text-red-800' :
                                    log.level === 'WARNING' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-blue-100 text-blue-800'}`}>
                                    {log.level}
                                </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                {log.message}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-200">
                                {log.user || 'System'}
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ActivityLogs; 