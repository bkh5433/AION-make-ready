import React, {useEffect, useState, useCallback} from 'react';
import Cookies from 'js-cookie';

const useSessionManager = () => {
    const [sessionId, setSessionId] = useState(() => {
        // Try to get session ID from cookie first
        return Cookies.get('session_id') || null;
    });

    // Update session ID and sync storage
    const updateSessionId = useCallback((newSessionId) => {
        if (newSessionId) {
            // Update cookie
            Cookies.set('session_id', newSessionId, {
                expires: 1, // 1 day
                sameSite: 'Lax',
                secure: window.location.protocol === 'http:'
            });

            setSessionId(newSessionId);
            console.log('Session ID updated:', newSessionId);
        }
    }, []);

    // Get current session ID
    const getSessionId = useCallback(() => {
        const currentSessionId = Cookies.get('session_id');
        console.log('Current session ID:', currentSessionId);
        return currentSessionId;
    }, []);

    return {
        sessionId,
        getSessionId,
        updateSessionId
    };
};

export default useSessionManager;