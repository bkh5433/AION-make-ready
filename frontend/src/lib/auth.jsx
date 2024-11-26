import React, {createContext, useContext, useState, useEffect} from 'react';
import {api} from './api';

const AuthContext = createContext(null);

export const AuthProvider = ({children}) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadUser = async () => {
            try {
                // Only attempt to load user if we have a token
                const token = localStorage.getItem('authToken');
                if (token) {
                    const {user} = await api.getCurrentUser();
                    setUser(user);
                }
            } catch (err) {
                console.error('Error loading user:', err);
                setError(err.message);
                // Clear invalid token
                localStorage.removeItem('authToken');
            } finally {
                setLoading(false);
            }
        };

        loadUser();
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