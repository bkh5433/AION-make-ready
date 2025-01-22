import React, {useState, useEffect} from 'react';
import {
    RefreshCw, Database, Clock, Server,
    Gauge, HardDrive, Activity, AlertTriangle,
    CheckCircle, Network, Users, AlertCircle,
    AlertOctagon, LogIn
} from 'lucide-react';
import {api} from '../../lib/api';
import {useImportWindow} from '../../lib/hooks/useImportWindow';
import {Tooltip} from '../ui/tooltip';

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

const SystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState(null);
    const [cacheStatus, setCacheStatus] = useState(null);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds
    const [autoRefresh, setAutoRefresh] = useState(true);
    const {isInImportWindow, lastImportWindow, error: importWindowError, checkStatus} = useImportWindow();
    const [isImportWindowLoading, setIsImportWindowLoading] = useState(false);
    const [importActionError, setImportActionError] = useState(null);
    const [showImportWarning, setShowImportWarning] = useState(false);
    const [pendingAction, setPendingAction] = useState(null);
    const [microsoftSSOEnabled, setMicrosoftSSOEnabled] = useState({dev: false, prod: false});
    const [isTogglingSSO, setIsTogglingSSO] = useState({dev: false, prod: false});
    const [showSSOWarning, setShowSSOWarning] = useState(false);
    const [pendingSSOAction, setPendingSSOAction] = useState(null);
    const [remoteInfo, setRemoteInfo] = useState(null);
    const [isSettingRemoteInfo, setIsSettingRemoteInfo] = useState(false);
    const [remoteInfoInput, setRemoteInfoInput] = useState({message: '', status: 'info'});

    useEffect(() => {
        fetchStatus();
        fetchMicrosoftSSOStatus();
        let interval;

        if (autoRefresh) {
            interval = setInterval(() => {
                fetchStatus();
                fetchMicrosoftSSOStatus();
            }, refreshInterval);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [autoRefresh, refreshInterval]);

    useEffect(() => {
        const fetchRemoteInfo = async () => {
            try {
                const response = await api.getRemoteInfo();
                if (response.success) {
                    setRemoteInfo(response.info);
                }
            } catch (error) {
                console.error('Error fetching remote info:', error);
            }
        };

        fetchRemoteInfo();
        if (autoRefresh) {
            const interval = setInterval(fetchRemoteInfo, refreshInterval);
            return () => clearInterval(interval);
        }
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

    const fetchMicrosoftSSOStatus = async () => {
        try {
            const response = await api.getMicrosoftSSOStatus();
            if (response.success) {
                setMicrosoftSSOEnabled({
                    dev: response.dev_enabled || false,
                    prod: response.prod_enabled || false
                });
            }
        } catch (error) {
            console.error('Error fetching Microsoft SSO status:', error);
        }
    };

    const handleToggleMicrosoftSSO = async (environment) => {
        if (!showSSOWarning) {
            setShowSSOWarning(true);
            setPendingSSOAction(environment);
            return;
        }

        try {
            setIsTogglingSSO(prev => ({...prev, [environment]: true}));
            const response = await api.toggleMicrosoftSSO(environment);
            if (response.success) {
                setMicrosoftSSOEnabled(prev => ({
                    ...prev,
                    [environment]: response.enabled
                }));
            }
        } catch (error) {
            console.error('Error toggling Microsoft SSO:', error);
        } finally {
            setIsTogglingSSO(prev => ({...prev, [environment]: false}));
            setShowSSOWarning(false);
            setPendingSSOAction(null);
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
                primary_record_count,
                fallback_record_count,
                confidence_score
            } = cacheStatus.version_info;

            details.push(`Primary Records: ${primary_record_count}`);
            details.push(`Fallback Records: ${fallback_record_count}`);

            if (confidence_score !== undefined) {
                details.push(
                    <div key="confidence" className="flex items-center gap-2">
                        <span>Confidence Score:</span>
                        <Tooltip content={getConfidenceScoreDetails(confidence_score)} wide>
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

        // Add import window status
        if (cacheStatus.update_info?.import_window_detected) {
            details.push(
                <div key="import-window" className="flex items-center gap-2 text-yellow-400">
                    <AlertTriangle className="w-4 h-4"/>
                    <span>Import Window Active</span>
                </div>
            );
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

    // Add helper function for confidence score tooltip content
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

    const getCacheStatus = () => {
        if (!cacheStatus) return 'unknown';
        if (cacheStatus.warnings?.length > 0) return 'warning';
        if (cacheStatus.refresh_state?.error) return 'error';
        return 'healthy';
    };

    const handleTriggerImportWindow = async (action) => {
        if (!showImportWarning) {
            setShowImportWarning(true);
            setPendingAction(action);
            return;
        }

        try {
            setIsImportWindowLoading(true);
            setImportActionError(null);
            await api.triggerImportWindow(action);
            await checkStatus();
        } catch (err) {
            console.error('Error triggering import window:', err);
            setImportActionError(err.message);
        } finally {
            setIsImportWindowLoading(false);
            setShowImportWarning(false);
            setPendingAction(null);
        }
    };

    const SSOToggleButton = ({environment, enabled, isToggling}) => (
        <button
            onClick={() => handleToggleMicrosoftSSO(environment)}
            disabled={isToggling}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors
                ${enabled
                ? 'bg-green-900/50 text-green-400 hover:bg-green-900/70'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
        >
            {isToggling ? (
                <RefreshCw className="w-4 h-4 animate-spin"/>
            ) : (
                <LogIn className="w-4 h-4"/>
            )}
            {enabled ? 'Disable' : 'Enable'} {environment.toUpperCase()}
        </button>
    );

    // Add Import Window Testing Card
    const importWindowCard = (
        <div className="bg-white dark:bg-[#1f2937] rounded-lg shadow-md overflow-hidden">
            <div className="p-6 space-y-6">
                <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold">Database Import Controls</h3>
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium
                        ${isInImportWindow
                        ? 'bg-yellow-500/10 text-yellow-500'
                        : 'bg-green-500/10 text-green-500'}`}
                    >
                        {isInImportWindow ? (
                            <>
                                <AlertCircle className="w-4 h-4"/>
                                Import Active
                            </>
                        ) : (
                            <>
                                <CheckCircle className="w-4 h-4"/>
                                Normal Operation
                            </>
                        )}
                    </div>
                </div>

                <div className="space-y-4">
                    {lastImportWindow && (
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                            <span className="font-medium">Last Import Window:</span>
                            <span className="ml-2">{new Date(lastImportWindow).toLocaleString()}</span>
                        </div>
                    )}

                    <div className="flex gap-4">
                        <button
                            onClick={() => handleTriggerImportWindow('start')}
                            disabled={isImportWindowLoading || isInImportWindow}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                                ${isImportWindowLoading ? 'opacity-50 cursor-not-allowed' : ''}
                                ${isInImportWindow
                                ? 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
                                : 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                            }`}
                        >
                            {isImportWindowLoading ? (
                                <RefreshCw className="w-4 h-4 animate-spin"/>
                            ) : (
                                <Database className="w-4 h-4"/>
                            )}
                            Start Import
                        </button>

                        <button
                            onClick={() => handleTriggerImportWindow('end')}
                            disabled={isImportWindowLoading || !isInImportWindow}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
                                ${isImportWindowLoading ? 'opacity-50 cursor-not-allowed' : ''}
                                ${!isInImportWindow
                                ? 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
                                : 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700'
                            }`}
                        >
                            {isImportWindowLoading ? (
                                <RefreshCw className="w-4 h-4 animate-spin"/>
                            ) : (
                                <CheckCircle className="w-4 h-4"/>
                            )}
                            End Import
                        </button>
                    </div>

                    {(importWindowError || importActionError) && (
                        <div className="flex items-center gap-2 text-sm text-red-500 bg-red-500/10 p-3 rounded-lg">
                            <AlertCircle className="w-4 h-4 flex-shrink-0"/>
                            <span>
                                {importActionError || importWindowError}
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );

    // Add this new warning dialog component
    const importWarningDialog = showImportWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 max-w-md w-full mx-4">
                <div className="flex items-center gap-3 text-yellow-400 mb-4">
                    <AlertOctagon className="w-6 h-6"/>
                    <h3 className="text-lg font-semibold">Warning: Import Window Control</h3>
                </div>

                <p className="text-gray-300 mb-4">
                    {pendingAction === 'start' ? (
                        "Starting an import window will temporarily affect system performance and may impact user operations. Only proceed if a database import is required."
                    ) : (
                        "Ending the import window prematurely may result in incomplete data synchronization. Ensure all import operations are complete before proceeding."
                    )}
                </p>

                <div className="flex justify-end gap-3">
                    <button
                        onClick={() => {
                            setShowImportWarning(false);
                            setPendingAction(null);
                        }}
                        className="px-4 py-2 rounded-lg bg-gray-700 text-gray-200 hover:bg-gray-600 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => handleTriggerImportWindow(pendingAction)}
                        className="px-4 py-2 rounded-lg bg-yellow-600 text-white hover:bg-yellow-700 transition-colors"
                    >
                        Proceed
                    </button>
                </div>
            </div>
        </div>
    );

    const ssoWarningDialog = showSSOWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-xl border border-gray-700 max-w-md w-full mx-4">
                <div className="flex items-center gap-3 text-yellow-400 mb-4">
                    <AlertOctagon className="w-6 h-6"/>
                    <h3 className="text-lg font-semibold">Warning: SSO Configuration Change</h3>
                </div>

                <p className="text-gray-300 mb-4">
                    {microsoftSSOEnabled[pendingSSOAction] ? (
                        `Disabling Microsoft SSO for ${pendingSSOAction.toUpperCase()} environment will prevent users from logging in via Microsoft. They will need to use username/password authentication.`
                    ) : (
                        `Enabling Microsoft SSO for ${pendingSSOAction.toUpperCase()} environment will allow users to log in using their Microsoft accounts. Ensure Microsoft SSO is properly configured before proceeding.`
                    )}
                </p>

                <div className="flex justify-end gap-3">
                    <button
                        onClick={() => {
                            setShowSSOWarning(false);
                            setPendingSSOAction(null);
                        }}
                        className="px-4 py-2 rounded-lg bg-gray-700 text-gray-200 hover:bg-gray-600 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => handleToggleMicrosoftSSO(pendingSSOAction)}
                        className="px-4 py-2 rounded-lg bg-yellow-600 text-white hover:bg-yellow-700 transition-colors"
                    >
                        Proceed
                    </button>
                </div>
            </div>
        </div>
    );

    const handleSetRemoteInfo = async () => {
        try {
            setIsSettingRemoteInfo(true);
            const response = await api.setRemoteInfo(remoteInfoInput.message, remoteInfoInput.status);
            if (response.success) {
                const updatedInfo = await api.getRemoteInfo();
                if (updatedInfo.success) {
                    setRemoteInfo(updatedInfo.info);
                }
                setRemoteInfoInput({message: '', status: 'info'});
            }
        } catch (error) {
            console.error('Error setting remote info:', error);
        } finally {
            setIsSettingRemoteInfo(false);
        }
    };

    const handleClearRemoteInfo = async () => {
        try {
            setIsSettingRemoteInfo(true);
            const response = await api.clearRemoteInfo();
            if (response.success) {
                setRemoteInfo(null);
            }
        } catch (error) {
            console.error('Error clearing remote info:', error);
        } finally {
            setIsSettingRemoteInfo(false);
        }
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

            {/* Authentication Settings */}
            <div>
                <h3 className="text-xl font-semibold text-gray-200 mb-4">Authentication Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <MetricCard
                        title="Microsoft SSO"
                        icon={LogIn}
                        status={microsoftSSOEnabled.prod ? 'healthy' : 'warning'}
                        value={
                            <div className="flex flex-col gap-1">
                                <span
                                    className={`text-sm ${microsoftSSOEnabled.dev ? 'text-green-400' : 'text-gray-400'}`}>
                                    Dev: {microsoftSSOEnabled.dev ? 'Enabled' : 'Disabled'}
                                </span>
                                <span
                                    className={`text-sm ${microsoftSSOEnabled.prod ? 'text-green-400' : 'text-gray-400'}`}>
                                    Prod: {microsoftSSOEnabled.prod ? 'Enabled' : 'Disabled'}
                                </span>
                            </div>
                        }
                        details={
                            <div className="flex flex-col gap-2">
                                <p>Toggle Microsoft SSO status for each environment</p>
                                <div className="flex flex-col gap-2">
                                    <SSOToggleButton
                                        environment="dev"
                                        enabled={microsoftSSOEnabled.dev}
                                        isToggling={isTogglingSSO.dev}
                                    />
                                    <SSOToggleButton
                                        environment="prod"
                                        enabled={microsoftSSOEnabled.prod}
                                        isToggling={isTogglingSSO.prod}
                                    />
                                </div>
                            </div>
                        }
                    />
                </div>
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
                                `Last ${systemStatus.performance.searchMetrics.count} searches:\n` +
                                `Avg Time: ${formatResponseTime(systemStatus.performance.searchMetrics.avgQueryTime)}\n` +
                                `P95: ${formatResponseTime(systemStatus.performance.searchMetrics.p95QueryTime)}\n` +
                                `Avg Results: ${systemStatus.performance.searchMetrics.avgResultsCount}` :
                                systemStatus?.performance?.routeResponseTimes?.search ?
                                    `Average response time for search operations` :
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
                            systemStatus?.performance?.taskMetrics ?
                                `Queue Status:\n` +
                                `Active: ${systemStatus.performance.taskMetrics.activeTasks}\n` +
                                `Queued: ${systemStatus.performance.taskMetrics.queuedTasks}\n` +
                                `Success Rate: ${systemStatus.performance.taskMetrics.successRate}%\n` +
                                `Completed: ${systemStatus.performance.taskMetrics.completedTasks}` :
                                systemStatus?.performance?.routeResponseTimes?.generation ?
                                    `Average response time for report generation` :
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
                            systemStatus?.performance ? 
                                `Last Hour:\n` +
                                `Total Requests: ${systemStatus.performance.totalRequests}\n` +
                                `Recent Errors: ${systemStatus.performance.recentErrors}` :
                                'Error rate in last hour'
                        }
                    />
                </div>
            </div>

            {/* Remote Info Message */}
            <MetricCard
                title="Remote Info Message"
                icon={AlertCircle}
                status={remoteInfo ? remoteInfo.status : 'info'}
                value={remoteInfo ? remoteInfo.message : 'No message set'}
                details={
                    <div className="space-y-4">
                        <div className="flex flex-col gap-2">
                            <input
                                type="text"
                                value={remoteInfoInput.message}
                                onChange={(e) => setRemoteInfoInput(prev => ({...prev, message: e.target.value}))}
                                placeholder="Enter message"
                                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <select
                                value={remoteInfoInput.status}
                                onChange={(e) => setRemoteInfoInput(prev => ({...prev, status: e.target.value}))}
                                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-md text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="info">Info</option>
                                <option value="extended">Warning</option>
                                <option value="critical">Critical</option>
                            </select>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleSetRemoteInfo}
                                disabled={isSettingRemoteInfo || !remoteInfoInput.message}
                                className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors
                                    ${isSettingRemoteInfo || !remoteInfoInput.message
                                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700'}`}
                            >
                                {isSettingRemoteInfo ? (
                                    <RefreshCw className="w-4 h-4 animate-spin"/>
                                ) : (
                                    'Set Message'
                                )}
                            </button>
                            {remoteInfo && (
                                <button
                                    onClick={handleClearRemoteInfo}
                                    disabled={isSettingRemoteInfo}
                                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors
                                        ${isSettingRemoteInfo
                                        ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                                        : 'bg-red-600/20 text-red-400 hover:bg-red-600/30'}`}
                                >
                                    Clear
                                </button>
                            )}
                        </div>
                    </div>
                }
            />

            {importWindowCard}
            {ssoWarningDialog}
            {importWarningDialog}
        </div>
    );
};

export default SystemStatus;