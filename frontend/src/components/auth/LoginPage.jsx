import React, {useState, useEffect} from 'react';
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
    const [formData, setFormData] = useState({
        username: '',
        password: ''
    });

    useEffect(() => {
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

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-border/50"></div>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span
                                className="bg-card px-4 py-1 text-muted-foreground/70 rounded-full border border-border/50">Or</span>
                        </div>
                    </div>

                    {/* Traditional Login Form */}
                    <form onSubmit={handleSubmit} className="space-y-6">
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
                </CardContent>
            </Card>
        </div>
    );
};

export default LoginPage; 