import React, {useState, useEffect} from 'react';
import {
    RefreshCw, Database, Clock, Server,
    Gauge, HardDrive, Activity, AlertTriangle,
    CheckCircle, Network, Users
} from 'lucide-react';
import {api} from '../../lib/api';

const MetricCard = ({title, value, icon: Icon, status, details, onClick}) => (
    <div
        className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow duration-200">
        <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">{title}</h3>
            <div className="flex items-center gap-2">
                {onClick && (
                    <button
                        onClick={onClick}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full"
                    >
                        <RefreshCw className={`h-5 w-5 ${status === 'loading' ? 'animate-spin' : ''}`}/>
                    </button>
                )}
                <Icon className="h-5 w-5 text-gray-400"/>
            </div>
        </div>
        <div className="mt-4">
            {status && (
                <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                    ${status === 'healthy' ? 'bg-green-100 text-green-800' :
                    status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                        status === 'error' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'}`}>
                    {status === 'healthy' ? <CheckCircle className="w-3 h-3 mr-1"/> :
                        status === 'warning' ? <AlertTriangle className="w-3 h-3 mr-1"/> :
                            status === 'error' ? <AlertTriangle className="w-3 h-3 mr-1"/> : null}
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                </div>
            )}
            {value && <div className="mt-2 text-2xl font-semibold">{value}</div>}
            {details && <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{details}</p>}
        </div>
    </div>
);

const SystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState(null);
    const [cacheStatus, setCacheStatus] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        fetchStatus();
        let interval;

        if (autoRefresh) {
            interval = setInterval(fetchStatus, refreshInterval);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [autoRefresh, refreshInterval]);

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

    const formatBytes = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    };

    const getResourceStatus = (usage) => {
        if (!usage) return 'unknown';
        if (usage >= 90) return 'error';
        if (usage >= 70) return 'warning';
        return 'healthy';
    };

    const getCacheHitRate = () => {
        if (!cacheStatus?.performance_metrics) return 0;
        const {access_count, stale_data_served_count} = cacheStatus.performance_metrics;
        if (!access_count) return 0;
        const hits = access_count - (stale_data_served_count || 0);
        return ((hits / access_count) * 100).toFixed(1);
    };

    const getCacheDetails = () => {
        if (!cacheStatus) return 'No cache data available';

        const details = [];

        // Add last refresh time
        if (cacheStatus.update_info?.last_refresh) {
            details.push(`Last Refresh: ${new Date(cacheStatus.update_info.last_refresh).toLocaleString()}`);
        }

        // Add version info
        if (cacheStatus.version_info) {
            const {record_count, stale_record_count} = cacheStatus.version_info;
            details.push(`Records: ${record_count} (${stale_record_count} stale)`);
        }

        // Add performance metrics
        if (cacheStatus.performance_metrics) {
            const {access_count, refresh_count, failed_refreshes} = cacheStatus.performance_metrics;
            details.push(`Accesses: ${access_count}`);
            details.push(`Refreshes: ${refresh_count} (${failed_refreshes} failed)`);
        }

        // Add warnings if any
        if (cacheStatus.warnings?.length > 0) {
            details.push(`Warnings: ${cacheStatus.warnings.join(', ')}`);
        }

        return details.join('\n');
    };

    const getCacheStatus = () => {
        if (!cacheStatus) return 'unknown';
        if (cacheStatus.warnings?.length > 0) return 'warning';
        if (cacheStatus.refresh_state?.error) return 'error';
        return 'healthy';
    };

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">System Status</h2>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <label className="text-sm">Auto-refresh:</label>
                        <select
                            value={autoRefresh ? refreshInterval : 'off'}
                            onChange={(e) => {
                                const value = e.target.value;
                                setAutoRefresh(value !== 'off');
                                if (value !== 'off') setRefreshInterval(Number(value));
                            }}
                            className="text-sm rounded-md border-gray-300"
                        >
                            <option value="off">Off</option>
                            <option value="10000">10s</option>
                            <option value="30000">30s</option>
                            <option value="60000">1m</option>
                        </select>
                    </div>
                    <button
                        onClick={fetchStatus}
                        className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                        <RefreshCw className="h-4 w-4"/>
                        Refresh
                    </button>
                </div>
            </div>

            {/* System Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <MetricCard
                    title="System Health"
                    icon={Server}
                    status={systemStatus?.healthy ? 'healthy' : 'error'}
                    details={systemStatus?.details}
                />

                <MetricCard
                    title="Cache Status"
                    icon={Database}
                    status={getCacheStatus()}
                    value={`${getCacheHitRate()}% Hit Rate`}
                    details={getCacheDetails()}
                    onClick={handleRefreshCache}
                />

                <MetricCard
                    title="Active Users"
                    icon={Users}
                    value={systemStatus?.activeUsers || '0'}
                    status="healthy"
                    details="Currently active users in the system"
                />
            </div>

            {/* Resource Metrics */}
            <h3 className="text-xl font-semibold mt-8 mb-4">Resource Utilization</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    title="CPU Usage"
                    icon={Gauge}
                    value={`${systemStatus?.cpu?.usage || 0}%`}
                    status={getResourceStatus(systemStatus?.cpu?.usage)}
                    details={`${systemStatus?.cpu?.cores || 0} Cores`}
                />

                <MetricCard
                    title="Memory Usage"
                    icon={Database}
                    value={`${systemStatus?.memory?.usage || 0}%`}
                    status={getResourceStatus(systemStatus?.memory?.usage)}
                    details={`${formatBytes(systemStatus?.memory?.used || 0)} / ${formatBytes(systemStatus?.memory?.total || 0)}`}
                />

                <MetricCard
                    title="Disk Usage"
                    icon={HardDrive}
                    value={`${systemStatus?.disk?.usage || 0}%`}
                    status={getResourceStatus(systemStatus?.disk?.usage)}
                    details={`${formatBytes(systemStatus?.disk?.used || 0)} / ${formatBytes(systemStatus?.disk?.total || 0)}`}
                />

                <MetricCard
                    title="Network"
                    icon={Network}
                    value={formatBytes(systemStatus?.network?.bytesPerSec || 0) + '/s'}
                    status="healthy"
                    details={`↑${formatBytes(systemStatus?.network?.sent || 0)} ↓${formatBytes(systemStatus?.network?.received || 0)}`}
                />
            </div>

            {/* Performance Metrics */}
            <h3 className="text-xl font-semibold mt-8 mb-4">Performance Metrics</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <MetricCard
                    title="Response Time"
                    icon={Activity}
                    value={`${systemStatus?.performance?.responseTime || 0}ms`}
                    status={
                        !systemStatus?.performance?.responseTime ? 'unknown' :
                            systemStatus.performance.responseTime < 100 ? 'healthy' :
                                systemStatus.performance.responseTime < 300 ? 'warning' : 'error'
                    }
                    details={
                        systemStatus?.performance?.routeResponseTimes ?
                            `Search: ${systemStatus.performance.routeResponseTimes.search}ms\n` +
                            `Generation: ${systemStatus.performance.routeResponseTimes.generation}ms\n` +
                            `Data Fetch: ${systemStatus.performance.routeResponseTimes.data_fetch}ms` :
                            'Average API response time'
                    }
                />

                <MetricCard
                    title="Error Rate"
                    icon={AlertTriangle}
                    value={`${systemStatus?.performance?.errorRate || 0}%`}
                    status={
                        !systemStatus?.performance?.errorRate ? 'unknown' :
                            systemStatus.performance.errorRate < 1 ? 'healthy' :
                                systemStatus.performance.errorRate < 5 ? 'warning' : 'error'
                    }
                    details="API error rate in last hour"
                />

                <MetricCard
                    title="Cache Performance"
                    icon={Database}
                    value={`${cacheStatus?.performance_metrics?.avg_refresh_time?.toFixed(2) || 0}ms`}
                    status={
                        !cacheStatus?.performance_metrics?.avg_refresh_time ? 'unknown' :
                            cacheStatus.performance_metrics.avg_refresh_time < 1000 ? 'healthy' :
                                cacheStatus.performance_metrics.avg_refresh_time < 5000 ? 'warning' : 'error'
                    }
                    details={`Avg. refresh time\nWait time: ${cacheStatus?.performance_metrics?.avg_wait_time?.toFixed(2) || 0}ms`}
                />
            </div>
        </div>
    );
};

export default SystemStatus;