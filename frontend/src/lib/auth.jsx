import React, {createContext, useContext, useState, useEffect} from 'react';
import {api} from './api';

const AuthContext = createContext(null);

export const AuthProvider = ({children}) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let authCheckPromise = null;

        const checkAuth = async () => {
            try {
                const token = localStorage.getItem('authToken');
                if (token) {
                    if (!authCheckPromise) {
                        authCheckPromise = api.getCurrentUser();
                    }
                    const response = await authCheckPromise;
                    setUser(response.user);
                }
            } catch (error) {
                console.error('Auth check failed:', error);
                localStorage.removeItem('authToken');
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();

        // Cleanup function
        return () => {
            authCheckPromise = null;
        };
    }, []);

    const login = async (credentials) => {
        try {
            const response = await api.login(credentials);
            setUser(response.user);
            return response;
        } catch (err) {
            setError(err.message);
            throw err;
        }
    };

    const logout = () => {
        api.logout();
        setUser(null);
    };

    const value = {
        user,
        loading,
        error,
        login,
        logout,
        setUser
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}; 