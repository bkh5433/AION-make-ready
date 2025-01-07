// eslint-disable-next-line no-unused-vars
import React, {useEffect} from 'react';
import {useNavigate, useLocation} from 'react-router-dom';
import {useAuth} from '../../lib/auth';
import {api} from '../../lib/api';

const MicrosoftCallback = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const {setUser} = useAuth();

    useEffect(() => {
        const handleCallback = async () => {
            try {
                const searchParams = new URLSearchParams(location.search);
                const token = searchParams.get('token');
                const error = searchParams.get('error');

                if (error) {
                    console.error('Authentication error:', error);
                    navigate('/login', {
                        replace: true,
                        state: {error: 'Authentication failed: ' + error}
                    });
                    return;
                }

                if (!token) {
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

                    // Redirect to home
                    navigate('/', {replace: true});
                } catch (error) {
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
        <div className="flex items-center justify-center min-h-screen">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
                <p className="mt-4 text-gray-600">Completing authentication...</p>
            </div>
        </div>
    );
};

export default MicrosoftCallback; 