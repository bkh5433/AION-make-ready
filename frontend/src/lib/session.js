// Session management utilities
export const getSessionId = () => {
    const cookies = document.cookie.split(';');
    const sessionCookie = cookies.find(cookie => cookie.trim().startsWith('session_id='));
    return sessionCookie ? sessionCookie.split('=')[1].trim() : null;
};

export const setSessionId = (sessionId) => {
    document.cookie = `session_id=${sessionId}; path=/; max-age=3600; SameSite=Lax`;
};

export const clearSessionId = () => {
    document.cookie = 'session_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
};

// Add the custom hook as default export
const useSessionManager = () => {
    return {
        sessionId: getSessionId(),
        updateSessionId: setSessionId,
        clearSessionId
    };
};

export default useSessionManager;