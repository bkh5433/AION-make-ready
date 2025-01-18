// eslint-disable-next-line no-unused-vars
import React, {useEffect} from 'react';
import {useNavigate, useLocation} from 'react-router-dom';
import {useAuth} from '../../lib/auth';
import {api} from '../../lib/api';

// Add helper function for delay
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

const MicrosoftCallback = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const {setUser} = useAuth();

    useEffect(() => {
        const handleCallback = async () => {
            try {
                // Start timing the process
                const startTime = Date.now();

                const searchParams = new URLSearchParams(location.search);
                const token = searchParams.get('token');
                const error = searchParams.get('error');

                if (error) {
                    // Ensure minimum delay even for errors
                    await delay(1500);
                    console.error('Authentication error:', error);
                    navigate('/login', {
                        replace: true,
                        state: {error: 'Authentication failed: ' + error}
                    });
                    return;
                }

                if (!token) {
                    await delay(2000);
                    console.error('No token found in URL');
                    navigate('/login', {
                        replace: true,
                        state: {error: 'No authentication token received'}
                    });
                    return;
                }

                // Store the token and expiration
                localStorage.setItem('authToken', token);

                // Calculate and store token expiration (24 hours from now)
                const expiresAt = new Date();
                expiresAt.setHours(expiresAt.getHours() + 24);
                localStorage.setItem('tokenExpiresAt', expiresAt.toISOString());
                localStorage.setItem('tokenExpiresIn', (24 * 60 * 60).toString()); // 24 hours in seconds

                try {
                    // Use the api utility to get user info
                    const {user} = await api.getCurrentUser();
                    setUser(user);

                    // Calculate how long the process took
                    const processTime = Date.now() - startTime;
                    // If process was faster than 1.5 seconds, wait the remaining time
                    if (processTime < 1500) {
                        await delay(1500 - processTime);
                    }

                    // Redirect to home
                    navigate('/', {replace: true});
                } catch (error) {
                    // Ensure minimum delay even for errors
                    const processTime = Date.now() - startTime;
                    if (processTime < 1500) {
                        await delay(1500 - processTime);
                    }

                    console.error('Failed to get user info:', error);
                    localStorage.removeItem('authToken');
                    localStorage.removeItem('tokenExpiresAt');
                    localStorage.removeItem('tokenExpiresIn');
                    navigate('/login', {
                        replace: true,
                        state: {error: 'Failed to get user information'}
                    });
                }
            } catch (error) {
                await delay(1500);
                console.error('Error during Microsoft callback:', error);
                navigate('/login', {
                    replace: true,
                    state: {error: 'An error occurred during authentication. Please try again.'}
                });
            }
        };

        handleCallback();
    }, [navigate, location, setUser]);

    return (
        <div
            className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-background to-background/95">
            <div
                className="w-full max-w-md bg-white dark:bg-[#1f2937] shadow-2xl rounded-lg border border-gray-200 dark:border-gray-700/50 backdrop-blur-sm p-8">
                <div className="flex flex-col items-center space-y-6">
                    {/* Logo */}
                    <img
                        src="/aion-logo.png"
                        alt="AION Logo"
                        className="w-12 h-12 object-contain"
                    />

                    {/* Title with Beta Badge */}
                    <div className="flex items-center gap-2">
                        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                            AION Vista
                        </h1>
                        <span className="px-2 py-0.5 text-xs font-medium rounded-full 
                            bg-blue-100 dark:bg-blue-900/50 
                            text-blue-600 dark:text-blue-400
                            border border-blue-200 dark:border-blue-800/50">
                            Beta
                        </span>
                    </div>

                    {/* Loading Animation */}
                    <div className="relative flex items-center justify-center">
                        {/* Outer pulsing ring */}
                        <div
                            className="absolute w-20 h-20 border-4 border-blue-200 dark:border-blue-700/50 rounded-full animate-[pulse_1.5s_ease-in-out_infinite]"></div>

                        {/* Inner spinning ring */}
                        <div
                            className="w-16 h-16 border-4 border-blue-500 dark:border-blue-400/90 rounded-full animate-[spin_1s_linear_infinite] border-t-transparent dark:border-t-transparent"></div>
                    </div>

                    {/* Status Message */}
                    <div className="space-y-2 text-center">
                        <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
                            Completing Authentication
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Please wait while we sign you in...
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MicrosoftCallback; 