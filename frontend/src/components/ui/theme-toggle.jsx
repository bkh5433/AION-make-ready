// src/components/ui/theme-toggle.jsx
import {Moon, Sun} from 'lucide-react';
import {useTheme} from '../../lib/theme';

export function ThemeToggle() {
    const {isDarkMode, toggleDarkMode} = useTheme();

    return (
        <button
            onClick={toggleDarkMode}
            className="fixed bottom-6 left-6 p-3 rounded-full bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Toggle Dark Mode"
        >
            {isDarkMode ? (
                <Sun className="w-5 h-5"/>
            ) : (
                <Moon className="w-5 h-5"/>
            )}
        </button>
    );
}

export default ThemeToggle;