import React, {useState, useEffect, useRef} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from '../ui/card';
import {useTheme} from "../../lib/theme";
import {AlertTriangle, CheckCircle, X, Lock, Mail} from 'lucide-react';
import {Link, useNavigate, useLocation} from 'react-router-dom';
import {api} from '../../lib/api';

const LoginPage = () => {
    const {theme} = useTheme();
    const navigate = useNavigate();
    const location = useLocation();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [notifications, setNotifications] = useState([]);
    const [apiHealth, setApiHealth] = useState('checking');
    const [retryCount, setRetryCount] = useState(0);
    const [lastChecked, setLastChecked] = useState(null);
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 2000; // 2 seconds
    const [formData, setFormData] = useState({
        username: '',
        password: ''
    });
    const hasShownError = useRef(false);
    const [showLegacyAuth, setShowLegacyAuth] = useState(false);

    // Get the status message based on current state
    const getStatusMessage = () => {
        switch (apiHealth) {
            case 'healthy':
                return 'System Online';
            case 'unhealthy':
                return 'Connection Failed';
            case 'checking':
                return retryCount > 0 ? `Retrying Connection (${retryCount}/${MAX_RETRIES})...` : 'Verifying Connection...';
            default:
                return 'Status Unknown';
        }
    };

    // Get detailed status information
    const getDetailedStatus = () => {
        switch (apiHealth) {
            case 'healthy':
                return (
                    <div className="space-y-2 text-left">
                        <div className="font-semibold text-green-500">System Status: Healthy</div>
                        <div className="space-y-1 text-sm">
                            <div>• API Endpoint: Active</div>
                            <div>• Connection: Stable</div>
                            <div>• Authentication: Ready</div>
                            <div>• Services: All Systems Go</div>
                        </div>
                    </div>
                );
            case 'unhealthy':
                return (
                    <div className="space-y-2 text-left">
                        <div className="font-semibold text-red-500">System Status: Error</div>
                        <div className="space-y-1 text-sm">
                            <div>• API Endpoint: Unreachable</div>
                            <div>• Connection: Failed</div>
                            <div className="pl-4 text-xs text-red-400/90">
                                - API Server Unavailable<br/>
                                - Check Network Connection<br/>
                                - Service May Be Down
                            </div>
                            <div>• Authentication: Unavailable</div>
                            <div>• Services: System Disruption</div>
                        </div>
                    </div>
                );
            case 'checking':
                return (
                    <div className="space-y-2 text-left">
                        <div className="font-semibold text-yellow-500">System Status: Checking</div>
                        <div className="space-y-1 text-sm">
                            <div>• API Endpoint: Verifying</div>
                            <div>• Connection: In Progress</div>
                            <div>• Authentication: Pending</div>
                            {retryCount > 0 && (
                                <div>• Retry Status: Attempt {retryCount} of {MAX_RETRIES}</div>
                            )}
                        </div>
                    </div>
                );
            default:
                return (
                    <div className="space-y-2 text-left">
                        <div className="font-semibold">System Status: Unknown</div>
                        <div className="space-y-1 text-sm">
                            <div>• System Status: Unavailable</div>
                            <div>• Connection: Unknown</div>
                            <div>• Services: Not Detected</div>
                        </div>
                    </div>
                );
        }
    };

    // Helper function for delay
    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    useEffect(() => {
        const validateAndRedirect = async () => {
            // Check for existing auth token
            const authToken = localStorage.getItem('authToken');
            if (authToken) {
                try {
                    // Verify the token is valid by getting current user
                    await api.getCurrentUser();
                    // If we get here, token is valid
                    navigate('/', {replace: true});
                    return;
                } catch (error) {
                    // Token is invalid, remove it
                    console.error('Invalid auth token:', error);
                    localStorage.removeItem('authToken');
                }
            }

            // Continue with normal login page initialization
            checkApiHealth();
        };

        validateAndRedirect();

        // Handle Microsoft callback
        const params = new URLSearchParams(location.search);
        const code = params.get('code');
        const error = params.get('error');

        if (code) {
            handleMicrosoftCallback(code);
        } else if (error) {
            addNotification('error', 'Microsoft login failed: ' + error);
        }
    }, [location]);

    const checkApiHealth = async (isRetry = false) => {
        // Only reset retry count if this is a fresh check
        if (!isRetry) {
            setRetryCount(0);
        }
        
        try {
            const isHealthy = await api.checkHealth();
            console.log('API Health Check Result:', isHealthy);
            setApiHealth(isHealthy ? 'healthy' : 'unhealthy');
            setLastChecked(new Date());
            setRetryCount(0);
        } catch (error) {
            console.error('API Health Check Error:', error);

            // Handle retries for any connection error
            const currentRetryCount = retryCount + 1;

            if (currentRetryCount < MAX_RETRIES) {
                setApiHealth('checking');
                setRetryCount(currentRetryCount);
                console.log(`Retry attempt ${currentRetryCount} of ${MAX_RETRIES}`);
                // Schedule next retry
                setTimeout(() => checkApiHealth(true), RETRY_DELAY);
                return;
            }

            // If max retries reached, show unhealthy state
            setApiHealth('unhealthy');
            setRetryCount(0);

            // Add a notification about API being unreachable
            addNotification('error',
                <div className="space-y-2">
                    <div>Unable to connect to the API server:</div>
                    <ul className="list-disc ml-4">
                        <li>The service may be temporarily down</li>
                        <li>Check your network connection</li>
                        <li>Try refreshing the page</li>
                    </ul>
                </div>,
                10000
            );
        }
    };

    const handleMicrosoftCallback = async (code) => {
        setIsLoading(true);
        try {
            const response = await api.handleMicrosoftCallback(code);
            if (response.success) {
                addNotification('success', 'Successfully logged in with Microsoft!');
                navigate('/');
            }
        } catch (error) {
            setError(error.message);
            addNotification('error', error.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleMicrosoftLogin = async () => {
        setIsLoading(true);
        try {
            await api.microsoftLogin();
        } catch (error) {
            setError(error.message);
            addNotification('error', error.message);
            setIsLoading(false);
        }
    };

    const addNotification = (type, message, duration = 5000) => {
        const id = Date.now();
        setNotifications(prev => [...prev, {id, type, message}]);
        if (duration) {
            setTimeout(() => removeNotification(id), duration);
        }
    };

    const removeNotification = (id) => {
        setNotifications(prev => prev.filter(notification => notification.id !== id));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const response = await api.login({
                username: formData.username.trim(),
                password: formData.password
            });

            if (response.success) {
                // Store the auth token
                localStorage.setItem('authToken', response.token);

                if (response.user.requirePasswordChange || formData.password === 'aion') {
                    addNotification('info', 'Please change your password before continuing');
                    navigate('/change-password');
                } else {
                    addNotification('success', 'Successfully logged in!');
                    navigate('/');
                }
            } else {
                setError(response.message || 'Login failed');
                addNotification('error', response.message || 'Login failed');
            }
        } catch (error) {
            const errorMessage = error.message || 'An error occurred during login';
            setError(errorMessage);
            addNotification('error', errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const {name, value} = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    return (
        <div
            className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-background to-background/95">
            {/* Notifications Container */}
            <div className="fixed top-4 right-4 z-50 space-y-3">
                {notifications.map(notification => (
                    <div
                        key={notification.id}
                        className={`flex items-center gap-2 p-4 rounded-lg shadow-lg backdrop-blur-sm slide-in-from-right transform transition-all duration-300 hover:translate-x-[-4px] hover:shadow-xl ${
                            notification.type === 'success'
                                ? 'bg-green-500/90 text-white'
                                : notification.type === 'error'
                                    ? 'bg-red-500/90 text-white'
                                    : 'bg-blue-500/90 text-white'
                        }`}
                    >
                        {notification.type === 'success' && <CheckCircle className="h-5 w-5"/>}
                        {notification.type === 'error' && <X className="h-5 w-5"/>}
                        {notification.type === 'info' && <AlertTriangle className="h-5 w-5"/>}
                        <p>{notification.message}</p>
                        <button
                            onClick={() => removeNotification(notification.id)}
                            className="ml-2 hover:opacity-80"
                        >
                            <X className="h-4 w-4"/>
                        </button>
                    </div>
                ))}
            </div>

            <Card
                className="w-full max-w-md bg-card/80 backdrop-blur-sm shadow-2xl border border-border/50 transition-all duration-200">
                <CardHeader className="space-y-2 p-8">
                    <CardTitle
                        className="text-3xl font-bold text-center bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text text-transparent">
                        Welcome to AION Vista
                    </CardTitle>
                    <p className="text-center text-muted-foreground/80 text-lg">
                        Sign in to access the dashboard
                    </p>
                </CardHeader>
                <CardContent className="p-8 space-y-8">
                    {error && (
                        <div
                            className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive backdrop-blur-sm">
                            <p className="text-sm flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4"/>
                                {error}
                            </p>
                        </div>
                    )}

                    {/* Microsoft Login Button - Primary */}
                    <button
                        type="button"
                        onClick={handleMicrosoftLogin}
                        disabled={isLoading}
                        className={`w-full flex items-center justify-center gap-3 px-6 py-4 rounded-lg
                        bg-[#2F2F2F] text-white hover:bg-[#404040]
                        transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] hover:shadow-lg
                        ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        <svg className="h-6 w-6" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M10 0H0V10H10V0Z" fill="#F25022"/>
                            <path d="M21 0H11V10H21V0Z" fill="#7FBA00"/>
                            <path d="M10 11H0V21H10V11Z" fill="#00A4EF"/>
                            <path d="M21 11H11V21H21V11Z" fill="#FFB900"/>
                        </svg>
                        <span className="text-lg">Sign in with Microsoft</span>
                    </button>

                    {/* Legacy Auth Toggle */}
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-border/50"></div>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <button
                                onClick={() => setShowLegacyAuth(prev => !prev)}
                                className="bg-card px-4 py-1 text-muted-foreground/50 hover:text-muted-foreground/70 rounded-full border border-border/50 transition-colors duration-200">
                                Legacy Sign In
                            </button>
                        </div>
                    </div>

                    {/* Traditional Login Form - Collapsible */}
                    {showLegacyAuth && (
                        <form onSubmit={handleSubmit} className="space-y-6 animate-in slide-in-from-top duration-300">
                            <div className="space-y-4">
                                <div className="relative group">
                                    <Mail
                                        className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground/70 group-hover:text-foreground/80 transition-colors duration-200"/>
                                    <input
                                        type="text"
                                        name="username"
                                        placeholder="Username or email"
                                        value={formData.username}
                                        onChange={handleInputChange}
                                        disabled={isLoading}
                                        className="pl-10 pr-4 py-3 w-full rounded-lg bg-input/50 backdrop-blur-sm
                                        border-border/50 text-foreground
                                        placeholder-muted-foreground/70 focus:ring-2 
                                        focus:ring-ring/50 focus:border-transparent transition-all duration-200
                                        hover:bg-input/70"
                                        required
                                    />
                                </div>

                                <div className="relative group">
                                    <Lock
                                        className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground/70 group-hover:text-foreground/80 transition-colors duration-200"/>
                                    <input
                                        type="password"
                                        name="password"
                                        placeholder="Password"
                                        value={formData.password}
                                        onChange={handleInputChange}
                                        disabled={isLoading}
                                        className="pl-10 pr-4 py-3 w-full rounded-lg bg-input/50 backdrop-blur-sm
                                        border-border/50 text-foreground
                                        placeholder-muted-foreground/70 focus:ring-2 
                                        focus:ring-ring/50 focus:border-transparent transition-all duration-200
                                        hover:bg-input/70"
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                className={`w-full flex items-center justify-center gap-2 px-6 py-4 rounded-lg
                                transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] 
                                bg-secondary/80 hover:bg-secondary text-secondary-foreground backdrop-blur-sm
                                hover:shadow-lg
                                ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                {isLoading ? (
                                    <>
                                        <div
                                            className="animate-spin h-5 w-5 border-2 border-current border-t-transparent rounded-full"/>
                                        <span className="text-lg">Signing in...</span>
                                    </>
                                ) : (
                                    <span className="text-lg">Sign in with Email</span>
                                )}
                            </button>
                        </form>
                    )}

                    {/* API Health Indicator */}
                    <div className="mt-8 flex items-center justify-center gap-2 text-sm text-muted-foreground/50">
                        <div className="relative group">
                            <div
                                style={{
                                    '--status-color': apiHealth === 'healthy'
                                        ? '34, 197, 94' // green-500
                                        : apiHealth === 'unhealthy'
                                            ? '239, 68, 68' // red-500
                                            : '234, 179, 8', // yellow-500
                                }}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors duration-500
                                    border border-border/5 backdrop-blur-sm
                                    relative overflow-hidden
                                    group-hover:border-border/10 group-hover:bg-muted/10`}>
                                {/* Background gradient layer */}
                                <div
                                    style={{
                                        background: apiHealth === 'healthy'
                                            ? 'linear-gradient(90deg, rgba(34, 197, 94, 0.08) 0%, rgba(34, 197, 94, 0.03) 20%, rgba(34, 197, 94, 0.08) 50%, rgba(34, 197, 94, 0.03) 80%, rgba(34, 197, 94, 0.08) 100%)'
                                            : apiHealth === 'unhealthy'
                                                ? 'linear-gradient(90deg, rgba(239, 68, 68, 0.08) 0%, rgba(239, 68, 68, 0.03) 20%, rgba(239, 68, 68, 0.08) 50%, rgba(239, 68, 68, 0.03) 80%, rgba(239, 68, 68, 0.08) 100%)'
                                                : 'linear-gradient(90deg, rgba(234, 179, 8, 0.08) 0%, rgba(234, 179, 8, 0.03) 20%, rgba(234, 179, 8, 0.08) 50%, rgba(234, 179, 8, 0.03) 80%, rgba(234, 179, 8, 0.08) 100%)',
                                        backgroundSize: '200% 100%'
                                    }}
                                    className="absolute inset-0 animate-gradient-flow"
                                />
                                {/* Content layer */}
                                <div className="relative flex items-center gap-2 z-10">
                                    <div
                                        className={`h-2 w-2 rounded-full transition-all duration-500 ${
                                            apiHealth === 'healthy'
                                                ? 'bg-green-500/70'
                                                : apiHealth === 'unhealthy'
                                                    ? 'bg-red-500/70'
                                                    : 'bg-yellow-500/70'
                                        }`}
                                    />
                                    <span
                                        className="transition-colors duration-300 group-hover:text-muted-foreground/80">
                                        {getStatusMessage()}
                                    </span>
                                </div>
                            </div>

                            {/* Detailed Status Tooltip */}
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 
                                          opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none
                                          select-none">
                                <div
                                    className="bg-popover/95 backdrop-blur-sm border border-border/50 p-3 rounded-lg shadow-lg">
                                    {getDetailedStatus()}
                                </div>
                                <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 
                                              w-2 h-2 rotate-45 bg-popover/95 border-r border-b border-border/50">
                                </div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default LoginPage; 