import React, {useState, useEffect} from 'react';
import {
    RefreshCw, Database, Clock, Server,
    Gauge, HardDrive, Activity, AlertTriangle,
    CheckCircle, Network, Users
} from 'lucide-react';
import {api} from '../../lib/api';
import {Tooltip} from '../ui/Tooltip';

const MetricCard = ({title, value, icon: Icon, status, details, onClick}) => (
    <div
        className="p-6 bg-gray-900 rounded-xl border border-gray-700 hover:border-gray-600 transition-all duration-200 shadow-lg relative overflow-hidden">
        <div className="relative z-10">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <Icon className={`h-5 w-5 ${
                        status === 'healthy' ? 'text-green-400' :
                            status === 'warning' ? 'text-yellow-400' :
                                status === 'error' ? 'text-red-400' :
                                    'text-gray-400'
                    }`}/>
                    <h3 className="text-lg font-medium text-gray-200">{title}</h3>
                </div>
                {onClick && (
                    <button
                        onClick={onClick}
                        className="p-2 hover:bg-gray-800 rounded-full transition-colors duration-200"
                    >
                        <RefreshCw className={`h-4 w-4 text-gray-400 ${status === 'loading' ? 'animate-spin' : ''}`}/>
                    </button>
                )}
            </div>
            <div className="space-y-3">
                {status && (
                    <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium
                        ${status === 'healthy' ? 'bg-green-900/50 text-green-400 ring-1 ring-green-400/50' :
                        status === 'warning' ? 'bg-yellow-900/50 text-yellow-400 ring-1 ring-yellow-400/50' :
                            status === 'error' ? 'bg-red-900/50 text-red-400 ring-1 ring-red-400/50' :
                                'bg-gray-800 text-gray-400 ring-1 ring-gray-500/50'}`}>
                        {status === 'healthy' ? <CheckCircle className="w-3 h-3 mr-1"/> :
                            status === 'warning' ? <AlertTriangle className="w-3 h-3 mr-1"/> :
                            status === 'error' ? <AlertTriangle className="w-3 h-3 mr-1"/> : null}
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                    </div>
                )}
                {value && (
                    <div className={`text-2xl font-bold ${
                        status === 'healthy' ? 'text-green-400' :
                            status === 'warning' ? 'text-yellow-400' :
                                status === 'error' ? 'text-red-400' :
                                    'text-gray-200'
                    }`}>
                        {value}
                    </div>
                )}
                {details && (
                    <div className="text-sm text-gray-400 whitespace-pre-line">
                        {details}
                    </div>
                )}
            </div>
        </div>
        <div className={`absolute inset-0 opacity-5 ${
            status === 'healthy' ? 'bg-green-500' :
                status === 'warning' ? 'bg-yellow-500' :
                    status === 'error' ? 'bg-red-500' :
                        'bg-gray-500'
        }`}/>
    </div>
);

const getResponseTimeStatus = (responseTime, operationType) => {
    // Different thresholds for different operation types
    const thresholds = {
        search: {warning: 200, error: 500},        // Search should be fast
        data_fetch: {warning: 500, error: 1000},   // Data fetching moderate
        generation: {warning: 5000, error: 15000}, // Report generation can take longer
        default: {warning: 300, error: 1000}       // Default thresholds
    };

    const limits = thresholds[operationType] || thresholds.default;

    if (!responseTime) return 'unknown';
    if (responseTime < limits.warning) return 'healthy';
    if (responseTime < limits.error) return 'warning';
    return 'error';
};

const formatResponseTime = (time) => {
    if (!time) return '0ms';
    if (time < 1000) return `${time}ms`;
    return `${(time / 1000).toFixed(1)}s`;
};

const getConfidenceScoreDetails = (score) => {
    if (!score && score !== 0) return 'No confidence data available';

    let rating;
    let explanation;

    if (score >= 0.9) {
        rating = 'Excellent';
        explanation = 'Data is fresh and reliable. All validation checks passed.';
    } else if (score >= 0.7) {
        rating = 'Good';
        explanation = 'Data is reliable but some metrics may be slightly delayed.';
    } else if (score >= 0.5) {
        rating = 'Fair';
        explanation = 'Data may be stale or some validation checks failed.';
    } else {
        rating = 'Poor';
        explanation = 'Data may be significantly outdated or failed validation.';
    }

    return `Confidence Score: ${(score * 100).toFixed(1)}%
Rating: ${rating}
${explanation}

Factors affecting score:
• Data freshness
• Validation success rate
• Update consistency
• Data completeness`;
};

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

        // Version info with enhanced confidence score display
        if (cacheStatus.version_info) {
            const {
                current_version,
                primary_record_count,
                fallback_record_count,
                confidence_score
            } = cacheStatus.version_info;
            details.push(`Records: ${primary_record_count} current / ${fallback_record_count} fallback`);
            if (current_version) details.push(`Version: ${current_version}`);
            if (confidence_score !== undefined) {
                details.push(
                    <div key="confidence" className="flex items-center gap-1">
                        <span>Confidence:</span>
                        <Tooltip content={getConfidenceScoreDetails(confidence_score)}>
                            <span className={`font-medium ${
                                confidence_score >= 0.9 ? 'text-green-400' :
                                    confidence_score >= 0.7 ? 'text-blue-400' :
                                        confidence_score >= 0.5 ? 'text-yellow-400' :
                                            'text-red-400'
                            }`}>
                                {(confidence_score * 100).toFixed(1)}%
                            </span>
                        </Tooltip>
                    </div>
                );
            }
        }

        // Add last refresh time
        if (cacheStatus.update_info?.last_refresh) {
            details.push(`Last Refresh: ${new Date(cacheStatus.update_info.last_refresh).toLocaleString()}`);
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

        return (
            <div className="space-y-1">
                {details.map((detail, index) =>
                    typeof detail === 'string' ? (
                        <div key={index}>{detail}</div>
                    ) : detail
                )}
            </div>
        );
    };

    const getCacheStatus = () => {
        if (!cacheStatus) return 'unknown';
        if (cacheStatus.warnings?.length > 0) return 'warning';
        if (cacheStatus.refresh_state?.error) return 'error';
        return 'healthy';
    };

    return (
        <div className="space-y-8 p-6">
            {/* Controls */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-200">System Status</h2>
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
                        onClick={fetchStatus}
                        className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
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
            <div>
                <h3 className="text-xl font-semibold text-gray-200 mb-4">Resource Utilization</h3>
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
            </div>

            {/* Performance Metrics */}
            <div>
                <h3 className="text-xl font-semibold text-gray-200 mb-4">Performance Metrics</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Search Response Time */}
                    <MetricCard
                        title="Search Performance"
                        icon={Activity}
                        value={formatResponseTime(systemStatus?.performance?.routeResponseTimes?.search)}
                        status={getResponseTimeStatus(
                            systemStatus?.performance?.routeResponseTimes?.search,
                            'search'
                        )}
                        details={
                            systemStatus?.performance?.searchMetrics ?
                                `Avg: ${formatResponseTime(systemStatus.performance.searchMetrics.avg)}\n` +
                                `Min: ${formatResponseTime(systemStatus.performance.searchMetrics.min)}\n` +
                                `Max: ${formatResponseTime(systemStatus.performance.searchMetrics.max)}\n` +
                                `Last hour: ${systemStatus.performance.searchMetrics.count} searches` :
                                'No search metrics available'
                        }
                    />

                    {/* Report Generation */}
                    <MetricCard
                        title="Report Generation"
                        icon={Activity}
                        value={
                            systemStatus?.performance?.routeResponseTimes?.generation ?
                                `${formatResponseTime(systemStatus.performance.routeResponseTimes.generation)} avg` :
                                'No data'
                        }
                        status={getResponseTimeStatus(
                            systemStatus?.performance?.routeResponseTimes?.generation,
                            'generation'
                        )}
                        details={
                            systemStatus?.performance?.asyncMetrics ?
                                `Based on ${systemStatus.performance.asyncMetrics.completedGenerations} generations\n` +
                                `Active: ${systemStatus.performance.asyncMetrics.activeGenerations}\n` +
                                `Queue Size: ${systemStatus.performance.asyncMetrics.queueSize}\n` +
                                `Failed: ${systemStatus.performance.asyncMetrics.failedGenerations}` :
                                'No generation metrics available'
                        }
                    />

                    {/* Error Rate */}
                    <MetricCard
                        title="Error Rate"
                        icon={AlertTriangle}
                        value={`${systemStatus?.performance?.errorRate || 0}%`}
                        status={
                            !systemStatus?.performance?.errorRate ? 'unknown' :
                                systemStatus.performance.errorRate < 1 ? 'healthy' :
                                    systemStatus.performance.errorRate < 5 ? 'warning' : 'error'
                        }
                        details={
                            systemStatus?.performance?.errorMetrics ?
                                `Last Hour:\n` +
                                `API Errors: ${systemStatus.performance.errorMetrics.apiErrors}\n` +
                                `Auth Failures: ${systemStatus.performance.errorMetrics.authFailures}\n` +
                                `Validation Errors: ${systemStatus.performance.errorMetrics.validationErrors}` :
                                'Error rate in last hour'
                        }
                    />
                </div>
            </div>
        </div>
    );
};

export default SystemStatus;