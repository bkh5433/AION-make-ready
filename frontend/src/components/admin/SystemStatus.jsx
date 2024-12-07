import React, {useState, useEffect} from 'react';
import {RefreshCw, Database, Clock, Server} from 'lucide-react';
import {api} from '../../lib/api';

const SystemStatus = () => {
    const [cacheStatus, setCacheStatus] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);

    useEffect(() => {
        fetchCacheStatus();
    }, []);

    const fetchCacheStatus = async () => {
        try {
            const status = await api.getCacheStatus();
            setCacheStatus(status);
        } catch (error) {
            console.error('Error fetching cache status:', error);
        }
    };

    const handleRefreshCache = async () => {
        try {
            setIsRefreshing(true);
            await api.forceRefreshData();
            await fetchCacheStatus();
        } catch (error) {
            console.error('Error refreshing cache:', error);
        } finally {
            setIsRefreshing(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Cache Status Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
                    {/* Cache status details */}
                </div>

                {/* Additional status cards */}
            </div>

            {/* Detailed Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Performance metrics */}
                {/* System health indicators */}
            </div>
        </div>
    );
};

export default SystemStatus; 