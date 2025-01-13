import {getSessionId, setSessionId, clearSessionId} from './session';

// Ensure the base URL always uses HTTPS and ends with /api
export const API_BASE_URL = (() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL;
    console.log('API Base URL from env:', baseUrl);

    if (!baseUrl) {
        console.error('VITE_API_BASE_URL environment variable is not set. Please set EC2_HOST in your Amplify environment variables.');
        // In production, we want to make it obvious that the environment is not configured correctly
        if (import.meta.env.PROD) {
            alert('API URL is not configured. Please contact the administrator.');
        }
    }

    // Convert HTTP to HTTPS if needed
    let finalUrl = baseUrl || 'http://localhost:3000';
    if (import.meta.env.PROD && finalUrl.startsWith('http://')) {
        finalUrl = 'https://' + finalUrl.substring(7);
        console.log('Converted to HTTPS URL:', finalUrl);
    }

    // Add /api if needed
    finalUrl = finalUrl.endsWith('/api') ? finalUrl : `${finalUrl}/api`;
    console.log('Final API URL:', finalUrl);
    return finalUrl;
})();

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
const fetchWithErrorHandling = async (url, options = {}, skipTokenCheck = false) => {
    try {
        if (!skipTokenCheck && isTokenExpired()) {
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
            ...(token && !skipTokenCheck && {'Authorization': `Bearer ${token}`}),
            ...options.headers
        };

        const response = await fetch(url, {
            ...options,
            credentials: 'include',
            headers
        });

        if (!response.ok) {
            if (response.status === 401 && !skipTokenCheck) {
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

    getHealthEndpoint() {
        return `${API_BASE_URL}/health`;
    },

    async checkHealth() {
        try {
            // Simulate SSL certificate error
            // throw new TypeError("net::ERR_CERT_AUTHORITY_INVALID");

            // Real implementation
            const response = await fetchWithErrorHandling(
                `${API_BASE_URL}/health`,
                {},
                true // Skip token check for health endpoint
            );
            const data = await response.json();
            return data.status === 'healthy';
        } catch (error) {
            console.error('Health check failed:', error);
            // Check specifically for certificate errors
            if (error.message?.includes('Failed to fetch') ||
                error.message?.includes('TypeError') ||
                error.name === 'TypeError' ||
                error.message?.includes('ERR_CERT_AUTHORITY_INVALID') ||
                error.message?.includes('certificate')) {
                // Throw a specific error type for certificate issues
                const newError = new Error('SSL_CERTIFICATE_ERROR');
                newError.originalError = error;
                throw newError;
            }
            throw error; // Re-throw other errors
        }
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

    async checkReportStatus(taskId) {
        console.log('Checking status for task:', taskId);
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/reports/status/${taskId}`
        );
        const data = await response.json();

        // Enhanced logging for task status
        const status = data.status;
        const queuePosition = data.queue_position;
        const activeTasks = data.active_tasks;
        const startedAt = data.started_at;

        // Determine actual status based on started_at field
        // If started_at is null, the task is requested but not processing yet
        const actualStatus = (status === 'processing' && !startedAt) ? 'requested' : status;

        if (actualStatus === 'requested') {
            console.log(`Task ${taskId} is requested (Queue Position: ${queuePosition}, Active Tasks: ${activeTasks})`);
        } else if (actualStatus === 'processing') {
            console.log(`Task ${taskId} is processing (Active Tasks: ${activeTasks}, Started At: ${startedAt})`);
        } else if (actualStatus === 'completed') {
            console.log(`Task ${taskId} completed successfully with ${data.files?.length || 0} files`);
        } else if (actualStatus === 'failed') {
            console.error(`Task ${taskId} failed with error: ${data.error}`);
        }

        return {
            ...data,
            status: actualStatus,  // Override the status with our corrected version
            // Add helper flags for frontend state management
            isRequested: actualStatus === 'requested',
            isProcessing: actualStatus === 'processing',
            isCompleted: actualStatus === 'completed',
            isFailed: actualStatus === 'failed',
            queuePosition: queuePosition,
            activeTasks: activeTasks,
            startedAt: startedAt
        };
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

    async login({username, password}) {
        try {
            console.log('Attempting login with API URL:', `${API_BASE_URL}/auth/login`);
            const response = await fetchWithErrorHandling(
                `${API_BASE_URL}/auth/login`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({username, password})
                },
                true // Skip token check for login
            );

            const data = await response.json();
            console.log('Login response:', data);

            if (!data.token) {
                throw new Error('No token received from server');
            }

            // Store token and expiration
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('tokenExpiresAt', data.expires_at);
            localStorage.setItem('tokenExpiresIn', data.expires_in);

            return data;
        } catch (error) {
            console.error('Login error:', error);
            // Don't redirect on login error, let the component handle it
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
        const response = await fetchWithErrorHandling(`${API_BASE_URL}/admin/users`);
        return response.json();
    },

    async createUser(userData) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/auth/register`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: userData.username,
                    password: userData.password || 'aion',  // Default password if not provided
                    name: userData.name,
                    role: userData.role || 'user',
                    isActive: userData.isActive !== undefined ? userData.isActive : true
                })
            }
        );
        return response.json();
    },

    async updateUser(userId, userData) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/users/${userId}`,
            {
                method: 'PUT',
                body: JSON.stringify(userData)
            }
        );
        return response.json();
    },

    async deleteUser(userId) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/users/${userId}`,
            {
                method: 'DELETE'
            }
        );
        return response.json();
    },

    async resetUserPassword(userId) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/users/${userId}/reset-password`,
            {
                method: 'POST'
            }
        );
        return response.json();
    },

    async toggleUserStatus(userId, isActive) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/users/${userId}`,
            {
                method: 'PUT',
                body: JSON.stringify({is_active: isActive})
            }
        );
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

    // Admin endpoints
    async getCacheStatus() {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/cache/status`
        );
        return response.json();
    },

    async getActivityLogs(filter = 'all', startDate = null, endDate = null) {
        const params = new URLSearchParams();
        if (filter !== 'all') params.append('level', filter);
        if (startDate) params.append('start_date', startDate.toISOString());
        if (endDate) params.append('end_date', endDate.toISOString());

        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/logs?${params}`
        );
        return response.json();
    },

    async getSystemStatus() {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/system/status`
        );
        return response.json();
    },

    async forceRefreshData() {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/refresh`,
            {
                method: 'POST'
            }
        );
        return response.json();
    },

    async changePassword(currentPassword, newPassword) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/auth/change-password`,
            {
                method: 'POST',
                body: JSON.stringify({
                    currentPassword,
                    newPassword
                })
            }
        );
        return response.json();
    },

    async getImportWindowStatus() {
        const response = await fetchWithErrorHandling(`${API_BASE_URL}/import-window/status`);
        return response.json();
    },

    async triggerImportWindow(action) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/test/trigger-import-window`,
            {
                method: 'POST',
                body: JSON.stringify({action})
            }
        );
        return response.json();
    },

    async microsoftLogin() {
        try {
            const response = await fetchWithErrorHandling(
                `${API_BASE_URL}/auth/microsoft/login`,
                {
                    method: 'GET'
                },
                true // Skip token check for login
            );
            const data = await response.json();

            if (response.status === 501) {
                throw new Error('Microsoft SSO is not available. Please use username/password login.');
            }

            if (data.success && data.auth_url) {
                // Redirect to Microsoft login
                window.location.href = data.auth_url;
            } else {
                throw new Error(data.message || 'Failed to initiate Microsoft login');
            }
        } catch (error) {
            console.error('Microsoft login error:', error);
            throw error;
        }
    },

    async handleMicrosoftCallback(code) {
        try {
            const response = await fetchWithErrorHandling(
                `${API_BASE_URL}/auth/microsoft/callback?code=${code}`,
                {
                    method: 'GET'
                },
                true // Skip token check for callback
            );

            if (response.status === 501) {
                throw new Error('Microsoft SSO is not available. Please use username/password login.');
            }

            const data = await response.json();

            if (data.success && data.token) {
                // Store the auth token
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('tokenExpiresAt', data.expires_at);
                localStorage.setItem('tokenExpiresIn', data.expires_in);
                return data;
            } else {
                throw new Error(data.message || 'Microsoft authentication failed');
            }
        } catch (error) {
            console.error('Microsoft callback error:', error);
            throw error;
        }
    },

    async getMicrosoftSSOStatus() {
        const response = await fetchWithErrorHandling(`${API_BASE_URL}/admin/microsoft-sso/status`);
        return response.json();
    },

    async toggleMicrosoftSSO(environment) {
        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/admin/microsoft-sso/toggle`,
            {
                method: 'POST',
                body: JSON.stringify({environment})
            }
        );
        return response.json();
    },

    // Get remote info
    async getRemoteInfo() {
        try {
            const response = await fetch(`${API_BASE_URL}/remote-info`, {
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                }
            });
            return await response.json();
        } catch (error) {
            console.error('Error fetching remote info:', error);
            return {success: false, error: error.message};
        }
    },

    // Set remote info (admin only)
    async setRemoteInfo(message, status = 'info') {
        try {
            const response = await fetch(`${API_BASE_URL}/remote-info`, {
                method: 'POST',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({message, status})
            });
            return await response.json();
        } catch (error) {
            console.error('Error setting remote info:', error);
            return {success: false, error: error.message};
        }
    },

    // Clear remote info (admin only)
    async clearRemoteInfo() {
        try {
            const response = await fetch(`${API_BASE_URL}/remote-info`, {
                method: 'DELETE',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                }
            });
            return await response.json();
        } catch (error) {
            console.error('Error clearing remote info:', error);
            return {success: false, error: error.message};
        }
    }
};