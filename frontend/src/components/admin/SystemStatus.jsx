import React, {useState, useEffect} from 'react';
import {RefreshCw, Database, Clock, Server} from 'lucide-react';
import {api} from '../../lib/api';

const SystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState(null);
    const [cacheStatus, setCacheStatus] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);

    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        try {
            const [sysStatus, cacheData] = await Promise.all([
                api.getSystemStatus(),
                api.getCacheStatus()
            ]);
            setSystemStatus(sysStatus);
            setCacheStatus(cacheData);
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    };

    const handleRefreshCache = async () => {
        try {
            setIsRefreshing(true);
            await api.forceRefreshData();
            await fetchStatus();
        } catch (error) {
            console.error('Error refreshing cache:', error);
        } finally {
            setIsRefreshing(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* System Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* System Status */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-medium">System Status</h3>
                        <Server className="h-5 w-5 text-gray-400"/>
                    </div>
                    <div className="mt-4">
                        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                            ${systemStatus?.healthy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {systemStatus?.healthy ? 'Healthy' : 'Issues Detected'}
                        </div>
                        {systemStatus?.details && (
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                                {systemStatus.details}
                            </p>
                        )}
                    </div>
                </div>

                {/* Cache Status */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-medium">Cache Status</h3>
                        <button
                            onClick={handleRefreshCache}
                            disabled={isRefreshing}
                            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full"
                        >
                            <RefreshCw className={`h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`}/>
                        </button>
                    </div>
                    <div className="mt-4">
                        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                            ${cacheStatus?.healthy ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                            {cacheStatus?.status || 'Unknown'}
                        </div>
                        {cacheStatus?.lastUpdated && (
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                                Last Updated: {new Date(cacheStatus.lastUpdated).toLocaleString()}
                            </p>
                        )}
                    </div>
                </div>

                {/* Performance Metrics */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-medium">Performance</h3>
                        <Clock className="h-5 w-5 text-gray-400"/>
                    </div>
                    <div className="mt-4 space-y-3">
                        {systemStatus?.metrics?.map((metric, index) => (
                            <div key={index} className="flex justify-between items-center">
                                <span className="text-sm text-gray-600 dark:text-gray-300">{metric.name}</span>
                                <span className="text-sm font-medium">{metric.value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SystemStatus; 