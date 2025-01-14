import {useState, useEffect} from 'react';
import {api} from '../api';

const POLL_INTERVAL = 30000; // Increase to 30 seconds to match system status
let globalState = {
    isInImportWindow: false,
    lastImportWindow: null,
    consecutiveNulls: 0,
    lastCheck: null,
    subscribers: new Set(),
    checkPromise: null
};

const notifySubscribers = () => {
    globalState.subscribers.forEach(callback => callback());
};

const checkImportWindowStatus = async () => {
    // If there's already a check in progress, return that promise
    if (globalState.checkPromise) {
        return globalState.checkPromise;
    }

    // If we checked recently (within 2 seconds), use cached data
    if (globalState.lastCheck && Date.now() - globalState.lastCheck < 2000) {
        return Promise.resolve({
            in_import_window: globalState.isInImportWindow,
            last_import_window: globalState.lastImportWindow,
            consecutive_null_count: globalState.consecutiveNulls
        });
    }

    // Create new check promise
    globalState.checkPromise = api.getImportWindowStatus()
        .then(response => {
            globalState.isInImportWindow = response.in_import_window;
            globalState.lastImportWindow = response.last_import_window;
            globalState.consecutiveNulls = response.consecutive_null_count || 0;
            globalState.lastCheck = Date.now();
            notifySubscribers();
            return response;
        })
        .finally(() => {
            globalState.checkPromise = null;
        });

    return globalState.checkPromise;
};

// Start global polling
let globalInterval = null;
const ensurePolling = () => {
    if (!globalInterval && globalState.subscribers.size > 0) {
        checkImportWindowStatus(); // Initial check
        globalInterval = setInterval(checkImportWindowStatus, POLL_INTERVAL);
    }
};

const stopPolling = () => {
    if (globalInterval && globalState.subscribers.size === 0) {
        clearInterval(globalInterval);
        globalInterval = null;
    }
};

export const useImportWindow = () => {
    const [state, setState] = useState({
        isInImportWindow: globalState.isInImportWindow,
        lastImportWindow: globalState.lastImportWindow,
        consecutiveNulls: globalState.consecutiveNulls,
        isLoading: true,
        error: null
    });

    useEffect(() => {
        const updateState = () => {
            setState({
                isInImportWindow: globalState.isInImportWindow,
                lastImportWindow: globalState.lastImportWindow,
                consecutiveNulls: globalState.consecutiveNulls,
                isLoading: false,
                error: null
            });
        };

        // Subscribe to updates
        globalState.subscribers.add(updateState);
        ensurePolling();

        // Initial state update
        updateState();

        // Cleanup
        return () => {
            globalState.subscribers.delete(updateState);
            stopPolling();
        };
    }, []);

    const checkStatus = async () => {
        try {
            await checkImportWindowStatus();
        } catch (err) {
            setState(prev => ({...prev, error: err.message}));
        }
    };

    return {
        isInImportWindow: state.isInImportWindow,
        lastImportWindow: state.lastImportWindow,
        consecutiveNulls: state.consecutiveNulls,
        isLoading: state.isLoading,
        error: state.error,
        checkStatus
    };
};

export default useImportWindow; 