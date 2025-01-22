import React, {useState, useEffect} from 'react';
import {Card, Button, Switch, Space, Tooltip} from 'antd';
import {SyncOutlined, ApiOutlined, DatabaseOutlined} from '@ant-design/icons';
import {adminApi} from '../lib/api';

const AdminCenter = () => {
    const [logs, setLogs] = useState([]);
    const [systemStats, setSystemStats] = useState({
        apiHealth: 'healthy',
        cacheStatus: 'active',
        memoryUsage: '0',
        cpuLoad: '0',
        uptime: '0',
    });
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        // Initial load
        fetchSystemStats();
        fetchLogs();

        // Set up auto-refresh if enabled
        let interval;
        if (autoRefresh) {
            interval = setInterval(() => {
                fetchSystemStats();
                fetchLogs();
            }, 30000); // Refresh every 30 seconds
        }

        return () => clearInterval(interval);
    }, [autoRefresh]);

    const fetchSystemStats = async () => {
        try {
            const data = await adminApi.getSystemStats();
            setSystemStats(data);
        } catch (error) {
            console.error('Failed to fetch system stats:', error);
        }
    };

    const fetchLogs = async () => {
        try {
            const data = await adminApi.getLogs();
            setLogs(data);
        } catch (error) {
            console.error('Failed to fetch logs:', error);
        }
    };

    const handleCacheRefresh = async () => {
        try {
            await adminApi.refreshCache();
            fetchSystemStats(); // Refresh stats after cache clear
        } catch (error) {
            console.error('Failed to refresh cache:', error);
        }
    };

    return (
        <div className="admin-center">
            <div className="admin-header">
                <h1>Admin Center</h1>
                <Space>
                    <Tooltip title="Auto-refresh dashboard">
                        <Switch
                            checked={autoRefresh}
                            onChange={setAutoRefresh}
                            checkedChildren="Auto-refresh On"
                            unCheckedChildren="Auto-refresh Off"
                        />
                    </Tooltip>
                </Space>
            </div>

            <div className="admin-grid">
                {/* System Status Cards */}
                <Card title="API Health" className="status-card">
                    <ApiOutlined
                        className={`status-icon ${systemStats.apiHealth}`}
                    />
                    <div className="status-text">{systemStats.apiHealth}</div>
                </Card>

                <Card title="Cache Status" className="status-card">
                    <DatabaseOutlined
                        className={`status-icon ${systemStats.cacheStatus}`}
                    />
                    <div className="status-text">
                        {systemStats.cacheStatus}
                        <Button
                            type="primary"
                            icon={<SyncOutlined/>}
                            onClick={handleCacheRefresh}
                            className="refresh-button"
                        >
                            Refresh Cache
                        </Button>
                    </div>
                </Card>

                {/* System Metrics */}
                <Card title="System Metrics" className="metrics-card">
                    <div className="metric">
                        <span>Memory Usage:</span>
                        <span>{systemStats.memoryUsage}%</span>
                    </div>
                    <div className="metric">
                        <span>CPU Load:</span>
                        <span>{systemStats.cpuLoad}%</span>
                    </div>
                    <div className="metric">
                        <span>Uptime:</span>
                        <span>{systemStats.uptime}</span>
                    </div>
                </Card>

                {/* Logs Panel */}
                <Card title="System Logs" className="logs-card">
                    <div className="logs-container">
                        {logs.map((log, index) => (
                            <div key={index} className={`log-entry ${log.level}`}>
                                <span className="log-timestamp">{log.timestamp}</span>
                                <span className="log-level">{log.level}</span>
                                <span className="log-message">{log.message}</span>
                            </div>
                        ))}
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default AdminCenter; 