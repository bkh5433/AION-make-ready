import {useState, useEffect} from 'react';
import {api} from '../api';

const POLL_INTERVAL = 10000; // Reduce to 10 seconds for more responsive detection

export const useImportWindow = () => {
    const [isInImportWindow, setIsInImportWindow] = useState(false);
    const [lastImportWindow, setLastImportWindow] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const checkImportWindowStatus = async () => {
        try {
            const response = await api.getImportWindowStatus();
            console.log('Import window status:', response); // Add logging
            setIsInImportWindow(response.in_import_window);
            setLastImportWindow(response.last_import_window);
            setError(null);
        } catch (err) {
            console.error('Error checking import window status:', err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        // Initial check
        checkImportWindowStatus();

        // Set up polling
        const interval = setInterval(checkImportWindowStatus, POLL_INTERVAL);

        return () => clearInterval(interval);
    }, []);

    return {
        isInImportWindow,
        lastImportWindow,
        isLoading,
        error,
        checkStatus: checkImportWindowStatus
    };
};

export default useImportWindow; 