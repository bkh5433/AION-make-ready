import {getSessionId, setSessionId, clearSessionId} from './session';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

// Add this helper function at the top of the file
const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    return token ? {
        'Authorization': `Bearer ${token}`
    } : {};
};

export const isTokenExpired = () => {
    const expiresAt = localStorage.getItem('tokenExpiresAt');
    if (!expiresAt) return true;

    const expirationDate = new Date(expiresAt);
    const now = new Date();

    return now >= expirationDate;
};

// Common fetch wrapper with error handling and session management
const fetchWithErrorHandling = async (url, options = {}) => {
    try {
        if (isTokenExpired()) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('tokenExpiresAt');
            localStorage.removeItem('tokenExpiresIn');
            window.location.href = '/login';
            throw new Error('Session expired');
        }

        const token = localStorage.getItem('authToken');
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(token && {'Authorization': `Bearer ${token}`}),
            ...options.headers
        };

        const response = await fetch(url, {
            ...options,
            credentials: 'include',
            headers
        });

        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('authToken');
                window.location.href = '/login';
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

    async login({username, password}) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({username, password})
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Login failed');
            }

            const data = await response.json();

            // Store token and expiration
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('tokenExpiresAt', data.expires_at);
            localStorage.setItem('tokenExpiresIn', data.expires_in);

            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    },

    async register({username, password, name, role = 'user'}) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/auth/register`,
            {
                method: 'POST',
                body: JSON.stringify({username, password, name, role})
            }
        );
        return response.json();
    },

    async getCurrentUser() {
        const response = await fetchWithErrorHandling(`${API_BASE_URL}/auth/me`);
        return response.json();
    },

    logout() {
        localStorage.removeItem('authToken');
        window.location.href = '/login';
    },

    async listUsers() {
        const response = await fetchWithErrorHandling(`${API_BASE_URL}/users`);
        return response.json();
    },

    async updateUserRole(email, role) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/users/${email}/role`,
            {
                method: 'PUT',
                body: JSON.stringify({role})
            }
        );
        return response.json();
    },

    forceRefreshData: async () => {
        try {
            const response = await fetchWithErrorHandling(
                `${API_BASE_URL}/refresh`,
                {
                    method: 'POST'
                }
            );
            return response.json();
        } catch (error) {
            console.error('Error in forceRefreshData:', error);
            throw error;
        }
    },

    // Admin endpoints
    getUsers: async () => {
        const response = await authenticatedFetch('/api/admin/users');
        return response.json();
    },

    updateUser: async (userId, userData) => {
        const response = await authenticatedFetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
        return response.json();
    },

    getActivityLogs: async (filter = 'all') => {
        const response = await authenticatedFetch(`/api/admin/logs?type=${filter}`);
        return response.json();
    },

    getCacheStatus: async () => {
        const response = await authenticatedFetch('/api/cache/status');
        return response.json();
    }
};