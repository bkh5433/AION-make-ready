// src/lib/theme.jsx
import React, {createContext, useContext, useEffect, useState} from 'react';
import {Moon, Sun} from 'lucide-react';

// Create context for theme management
const ThemeContext = createContext({
    isDarkMode: false,
    toggleDarkMode: () => {
    },
});

// Custom hook for using theme
export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
};

// Theme provider component
export function ThemeProvider({children}) {
    const [isDarkMode, setIsDarkMode] = useState(() => {
        if (typeof window === 'undefined') return false;
        // Check local storage first
        const savedMode = localStorage.getItem('isDarkMode');
        if (savedMode !== null) {
            return JSON.parse(savedMode);
        }
        // If no saved preference, check system preference
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    useEffect(() => {
        // Update document class and local storage when dark mode changes
        if (isDarkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('isDarkMode', JSON.stringify(isDarkMode));
    }, [isDarkMode]);

    const toggleDarkMode = () => {
        setIsDarkMode(prev => !prev);
    };

    return (
        <ThemeContext.Provider value={{isDarkMode, toggleDarkMode}}>
            {children}
        </ThemeContext.Provider>
    );
}

export default ThemeProvider;