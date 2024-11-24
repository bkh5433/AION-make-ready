import {getSessionId, setSessionId, clearSessionId} from './session';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Common fetch wrapper with error handling and session management
const fetchWithErrorHandling = async (url, options = {}) => {
    try {
        const sessionId = getSessionId();
        console.debug('Current session ID:', sessionId);

        // Don't set empty cookies
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(sessionId && {'Cookie': `session_id=${sessionId}`}),
            ...options.headers
        };

        const response = await fetch(url, {
            ...options,
            credentials: 'include', // Important for cookie handling
            headers
        });

        // Handle session cookie from response
        const setCookieHeader = response.headers.get('Set-Cookie');
        if (setCookieHeader) {
            const sessionMatch = setCookieHeader.match(/session_id=([^;]+)/);
            if (sessionMatch) {
                const newSessionId = sessionMatch[1];
                setSessionId(newSessionId);
                console.debug('New session ID set:', newSessionId);
            }
        }

        if (!response.ok) {
            if (response.status === 401) {
                // Clear session and throw specific error
                clearSessionId();
                throw new Error('Session expired or invalid');
            }
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.message ||
                `Server returned ${response.status}: ${response.statusText}`
            );
        }

        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};

// Mock user for testing
const MOCK_USER = {
    email: 'test@example.com',
    password: 'password123',
    token: 'mock-jwt-token-12345'
};

export const api = {
    async searchProperties(searchTerm = '') {
        const params = new URLSearchParams();
        if (searchTerm) params.append('q', searchTerm);

        console.log('Fetching properties from:', `${API_BASE_URL}/properties/search?${params}`);

        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/properties/search?${params}`
        );

        const data = await response.json();
        console.log('Received data:', data);
        return data;
    },

    async generateReports(propertyKeys) {
        console.log('Generating reports for properties:', propertyKeys);

        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/reports/generate`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({properties: propertyKeys}),
            }
        );

        const data = await response.json();
        console.log('Generate reports response:', data);
        return data;
    },

    async downloadReport(filePath) {
        console.log('Downloading file:', filePath);
        const sessionId = getSessionId();

        if (!sessionId) {
            throw new Error('No active session. Please regenerate the reports.');
        }

        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/reports/download?file=${encodeURIComponent(filePath)}`,
            {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/octet-stream'
                }
            }
        );

        return response.blob();
    },

    async downloadReports(files, onProgress) {
        const blobs = [];
        let completedFiles = 0;

        for (const file of files) {
            try {
                const blob = await this.downloadReport(file.path);
                blobs.push({name: file.name, blob});
                completedFiles++;

                if (onProgress) {
                    onProgress({
                        type: 'progress',
                        completed: completedFiles,
                        total: files.length,
                        currentFile: file.name
                    });
                }
            } catch (error) {
                console.error(`Failed to download ${file.name}:`, error);
                throw error;
            }
        }

        return blobs;
    },

    async checkHealth() {
        try {
            const response = await fetchWithErrorHandling(`${API_BASE_URL}/health`);
            const data = await response.json();
            return data.status === 'healthy';
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    },

    async login({email, password}) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 800));

        // Mock authentication
        if (email === MOCK_USER.email && password === MOCK_USER.password) {
            return {
                token: MOCK_USER.token,
                user: {
                    email: MOCK_USER.email,
                    name: 'Test User'
                }
            };
        }

        // Simulate authentication failure
        throw new Error('Invalid email or password');
    }
};