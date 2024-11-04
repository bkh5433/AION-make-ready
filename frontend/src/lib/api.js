// TODO: FIX DOWNLOAD REGARDING SESSION NOT BEING PASSED
//  CURRENTLY THE SESSION ID IS NOT BEING PASSED TO THE DOWNLOAD FUNCTION
//  SERVER RETURNS A 401 ERROR
const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Common fetch wrapper with error handling and session management
const fetchWithErrorHandling = async (url, options = {}) => {
    try {
        const response = await fetch(url, {
            ...options,
            credentials: 'include',
            headers: {
                ...options.headers,
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        });

        // Log cookie information for debugging
        console.debug('Cookies after request:', document.cookie);

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(
                errorData?.message ||
                `Server returned ${response.status}: ${response.statusText}`
            );
        }

        return response;
    } catch (error) {
        console.error('API Error:', error);
        if (error instanceof TypeError && error.message === 'Failed to fetch') {
            throw new Error('Unable to connect to the API server.');
        }
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

        const response = await fetchWithErrorHandling(
            `${API_BASE_URL}/reports/download?file=${encodeURIComponent(filePath)}`,
            {
                method: 'GET',
                headers: {
                    'Accept': 'application/octet-stream',
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
    }
};