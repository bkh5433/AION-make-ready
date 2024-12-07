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
            const response = await api.getActivityLogs(filter);
            setLogs(response.logs);
        } catch (error) {
            console.error('Error fetching logs:', error);
        } finally {
            setIsLoading(false);
        }
    };

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
                            {/* Log data cells */}
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ActivityLogs; 