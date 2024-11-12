import React, {useState, useEffect} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from './ui/card';
import {Search, Download, FileDown, CheckCircle, X, Plus, AlertTriangle, Moon, Sun} from 'lucide-react';
import {useTheme} from "../lib/theme.jsx";
import {api} from '../lib/api';
import DownloadManager from './DownloadManager';
import FloatingDownloadButton from './FloatingDownloadButton';
import {ZipDownloader, createTimestampedZipName, formatFileSize} from '../lib/zipUtility';
import useSessionManager from '../lib/session';
import {getSessionId} from '../lib/session';

const PropertyReportGenerator = () => {
    const [properties, setProperties] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedProperties, setSelectedProperties] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [notifications, setNotifications] = useState([]);
    const [downloadProgress, setDownloadProgress] = useState(null);
    const [isDataUpToDate, setIsDataUpToDate] = useState(null); // null, true, or false
    const {sessionId, updateSessionId} = useSessionManager();
    const {isDarkMode} = useTheme();

    const [downloadManagerState, setDownloadManagerState] = useState({
        isVisible: false,
        showFloatingButton: false,
        files: []
    });
    const [isFirstLoad, setIsFirstLoad] = useState(true); // New state variable

    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        const fetchData = async () => {
            let attempts = 0;
            let success = false;


            while (!success) {
                try {
                    setIsLoading(true);
                    setError(null);

                    const response = await api.searchProperties(searchTerm);


                    console.log('API Response:', response);

                    // Ensure we have the data array
                    if (!Array.isArray(response.data)) {
                        throw new Error('Invalid response format');
                    }

                    // Check data age
                    if (response.data.length > 0) {
                        const firstItem = response.data[0];
                        const latestPostDateStr = firstItem.latest_post_date;
                        console.log('Latest Post Date String:', latestPostDateStr);

                        // Parse latest_post_date as a GMT date
                        const latestPostDate = new Date(latestPostDateStr);
                        console.log('Parsed Latest Post Date:', latestPostDate);

                        if (isNaN(latestPostDate)) {
                            throw new Error('Invalid latest_post_date format');
                        }

                        // Get yesterday's date at midnight GMT
                        const now = new Date();
                        const yesterday = new Date(Date.UTC(
                            now.getUTCFullYear(),
                            now.getUTCMonth(),
                            now.getUTCDate() - 1
                        ));
                        console.log('Yesterday\'s Date:', yesterday);

                        // Compare dates directly
                        if (latestPostDate.getTime() === yesterday.getTime()) {
                            setIsDataUpToDate(true);
                            console.log('Data is up-to-date');
                        } else {
                            setIsDataUpToDate(false);
                            console.log('Data is not up-to-date');
                        }
                    } else {
                        setIsDataUpToDate(null);
                        console.log('No data available');
                    }

                    // Map only the property_key and property_name
                    const formattedProperties = response.data.map(property => ({
                        PropertyKey: property.property_key || 0,  // Note the lowercase property_key
                        PropertyName: property.property_name || 'Unnamed Property'  // Note the lowercase property_name
                    }));

                    // Debug log the first few properties
                    console.log('First few formatted properties:', formattedProperties.slice(0, 3));

                    setTimeout(() => {

                        setProperties(formattedProperties);
                        setIsLoading(false);

                        if (isFirstLoad) {
                            addNotification('success', 'Successfully fetched properties');
                            setIsFirstLoad(false);
                        }
                    }, 1000);

                    success = true; // Mark as successful
                } catch (error) {

                    console.error(`Error fetching properties (Attempt ${attempts}):`, error);
                    setError(error.message);
                    setProperties([]);
                    addNotification('error', `${error.message || 'Error fetching properties (Attempt ${attempts})' || 'Unknown error occurred'}`);
                    await new Promise(resolve => setTimeout(resolve, 10000)); // Add a 10-second timeout between retries


                }
                attempts++;

            }
        };

        const delayDebounceFn = setTimeout(() => {
            fetchData();
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [searchTerm, isDarkMode]);

    // Debug properties before filtering
    // console.log('Properties before filtering:', properties);

    // Debug logging
    console.log('Raw properties before filtering:', properties);

    const filteredProperties = Array.isArray(properties)
        ? properties.filter(property => {
            // Debug log each property
            // console.log('Processing property:', property);

            return property &&
                property.PropertyName &&
                property.PropertyName.toLowerCase().includes(searchTerm.toLowerCase());
        })
        : [];

    // Debug log filtered results
    // console.log('Filtered properties:', filteredProperties);

    const togglePropertySelection = (propertyKey) => {
        setSelectedProperties(prev => {
            if (prev.includes(propertyKey)) {
                return prev.filter(key => key !== propertyKey);
            }
            return [...prev, propertyKey];
        });
    };

    const handleGenerateReports = async () => {
        if (selectedProperties.length === 0) {
            addNotification('error', 'Please select at least one property.');
            return;
        }

        setIsGenerating(true);
        addNotification('info', `Generating reports for ${selectedProperties.length} properties...`);

        try {
            const result = await api.generateReports(selectedProperties);

            if (result.success) {
                if (result.session_id) {
                    updateSessionId(result.session_id);
                    console.log('Session ID set after report generation:', result.session_id);
                }

                setNotifications([]);
                addNotification('success', `Successfully generated ${result.output.propertyCount} reports!`);
                setSelectedProperties([]);

                if (result.output?.files?.length) {
                    showDownloadManager(result.output.files, result.output.directory);
                }
            } else {
                throw new Error(result.message || 'Failed to generate reports');
            }
        } catch (error) {
            console.error('Error generating reports:', error);
            addNotification('error', `Failed to generate reports: ${error.message}`);
        } finally {
            setIsGenerating(false);
        }
    };

    // Add these notification helper functions right after your state declarations
    const addNotification = (type, message, duration = 5000) => {
        const id = Date.now();
        setNotifications(prev => [...prev, {id, type, message}]);
        if (duration) {
            setTimeout(() => {
                removeNotification(id);
            }, duration);
        }
    };

    const removeNotification = (id) => {
        setNotifications(prev => prev.filter(notification => notification.id !== id));
    };

    const hideDownloadManager = () => {
        setDownloadManagerState(prev => ({
            ...prev,
            isVisible: false,
            showFloatingButton: true // Keep showFloatingButton true when hiding manager
        }));
    };

// Update showDownloadManager function
    const showDownloadManager = (files, outputDirectory) => {
        // Process files to ensure correct paths without duplication
        const processedFiles = files.map(file => {
            // Remove any potential duplicate directory prefixes
            let normalizedPath = file;

            // Remove output directory prefix if it exists
            if (file.startsWith(outputDirectory + '/')) {
                normalizedPath = file.substring(outputDirectory.length + 1);
            }

            // Build the correct file path
            const fullPath = `${outputDirectory}/${normalizedPath}`;

            // Log for debugging
            console.log('Processing file:', {
                original: file,
                normalized: normalizedPath,
                fullPath: fullPath
            });

            return {
                name: normalizedPath.split('/').pop(), // Get just the filename
                path: fullPath,
                downloaded: false,
                downloading: false,
                failed: false
            };
        });

        console.log('Setting up download manager with files:', processedFiles);

        setDownloadManagerState({
            isVisible: true,
            showFloatingButton: true, // Always set to true when files are available
            files: processedFiles
        });
    };

// Update handleFloatingButtonClick function
    const handleFloatingButtonClick = () => {
        setDownloadManagerState(prev => ({
            ...prev,
            isVisible: true,
            showFloatingButton: true // Keep showFloatingButton true
        }));
    };

    const handleDownload = async (file) => {
        try {
            const currentSessionId = getSessionId();
            if (!currentSessionId) {
                throw new Error('No active session. Please regenerate the reports.');
            }

            setDownloadManagerState(prev => ({
                ...prev,
                files: prev.files.map(f =>
                    f.path === file.path
                        ? {...f, downloading: true}
                        : f
                )
            }));

            const blob = await api.downloadReport(file.path);

            // Create and trigger download
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = file.name;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);

            setDownloadManagerState(prev => ({
                ...prev,
                files: prev.files.map(f =>
                    f.path === file.path
                        ? {...f, downloading: false, downloaded: true}
                        : f
                )
            }));

            addNotification('success', `Successfully downloaded ${file.name}`);
        } catch (error) {
            console.error('Download error:', error);

            if (error.message.includes('session')) {
                // Session-specific error handling
                addNotification('error', 'Session expired. Please regenerate the reports.');
                // Optionally clear the download manager
                setDownloadManagerState(prev => ({
                    ...prev,
                    isVisible: false,
                    files: []
                }));
            } else {
                addNotification('error', `Failed to download ${file.name}: ${error.message}`);
            }

            setDownloadManagerState(prev => ({
                ...prev,
                files: prev.files.map(f =>
                    f.path === file.path
                        ? {...f, downloading: false, failed: true}
                        : f
                )
            }));
        }
    };

    // Add this function to handle downloading all files
    const handleDownloadAll = async (files) => {
        if (files.length > 3) {
            // Initialize ZipDownloader with callbacks
            const zipDownloader = new ZipDownloader({
                api,
                onProgress: (progress) => {
                    setDownloadProgress(progress);
                    if (progress.type === 'start') {
                        addNotification('info', progress.message);
                    }
                },
                onFileComplete: ({file}) => {
                    // Update individual file status in download manager
                    setDownloadManagerState(prev => ({
                        ...prev,
                        files: prev.files.map(f =>
                            f.path === file.path
                                ? {...f, downloading: false, downloaded: true}
                                : f
                        )
                    }));
                },
                onError: ({file, error}) => {
                    const message = file
                        ? `Failed to download ${file.name}: ${error}`
                        : `Download error: ${error}`;
                    addNotification('error', message);

                    // Reset file status if there was an error
                    if (file) {
                        setDownloadManagerState(prev => ({
                            ...prev,
                            files: prev.files.map(f =>
                                f.path === file.path
                                    ? {...f, downloading: false}
                                    : f
                            )
                        }));
                    }
                },
                onSuccess: ({fileCount, size}) => {
                    addNotification('success',
                        `Successfully downloaded ${fileCount} files (${formatFileSize(size)})`
                    );
                    setDownloadProgress(null);
                }
            });

            try {
                // Update all files to downloading state
                setDownloadManagerState(prev => ({
                    ...prev,
                    files: prev.files.map(f =>
                        files.some(df => df.path === f.path)
                            ? {...f, downloading: true}
                            : f
                    )
                }));

                // Start the zip download
                const zipName = createTimestampedZipName();
                await zipDownloader.downloadAsZip(files, zipName);

            } catch (error) {
                console.error('Failed to download files as ZIP:', error);
                // Reset all downloading states
                setDownloadManagerState(prev => ({
                    ...prev,
                    files: prev.files.map(f =>
                        files.some(df => df.path === f.path)
                            ? {...f, downloading: false}
                            : f
                    )
                }));
            } finally {
                setDownloadProgress(null);
            }
        } else {
            // Original sequential download logic for 3 or fewer files
            addNotification('info', `Starting download of ${files.length} files...`);

            for (const file of files) {
                try {
                    if (file.downloaded || file.downloading) continue;

                    setDownloadManagerState(prev => ({
                        ...prev,
                        files: prev.files.map(f =>
                            f.path === file.path
                                ? {...f, downloading: true}
                                : f
                        )
                    }));

                    await api.downloadReport(file.path);

                    setDownloadManagerState(prev => ({
                        ...prev,
                        files: prev.files.map(f =>
                            f.path === file.path
                                ? {...f, downloading: false, downloaded: true}
                                : f
                        )
                    }));

                    await new Promise(resolve => setTimeout(resolve, 500));

                } catch (error) {
                    console.error(`Error downloading ${file.name}:`, error);
                    addNotification('error', `Failed to download ${file.name}`);

                    setDownloadManagerState(prev => ({
                        ...prev,
                        files: prev.files.map(f =>
                            f.path === file.path
                                ? {...f, downloading: false}
                                : f
                        )
                    }));
                }
            }

            setDownloadManagerState(prev => {
                const allDownloaded = prev.files.every(f => f.downloaded);
                if (allDownloaded) {
                    addNotification('success', 'All files downloaded successfully!');
                }
                return prev;
            });
        }
    };


    return (
        <div className={`container mx-auto p-6 space-y-6 ${isDarkMode ? 'dark' : ''}`}>
            {/* Notifications */}
            <div className="fixed top-4 right-4 z-50 space-y-2">
                {notifications.map(({id, type, message}) => (
                    <div
                        key={id}
                        className={`flex items-center gap-3 p-4 rounded-lg shadow-lg max-w-md animate-in slide-in-from-right-5 ${
                            type === 'success' ? 'bg-green-50 border border-green-100' :
                                type === 'error' ? 'bg-red-50 border border-red-100' :
                                    'bg-blue-50 border border-blue-100'
                        }`}
                    >
                        {type === 'success' ? <CheckCircle className="h-5 w-5 text-green-500"/> :
                            type === 'error' ? <X className="h-5 w-5 text-red-500"/> :
                                <Plus className="h-5 w-5 text-blue-500"/>}
                        <p className="flex-1 text-sm text-gray-700">{message}</p>
                        <button
                            onClick={() => removeNotification(id)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            <X className="h-4 w-4"/>
                        </button>
                    </div>
                ))}
            </div>

            <Card className="bg-white dark:bg-gray-800 shadow-md">
                <CardHeader className="border-b border-gray-100 dark:border-gray-700">
                    <CardTitle className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
                        Property Report Generator
                    </CardTitle>
                </CardHeader>

                <CardContent className="space-y-6 pt-6">

                    {/* Data Age Status Message */}
                    {/* Data Age Status Message */}
                    {isDataUpToDate !== null && (
                        <div
                            className={`flex items-center gap-3 p-4 rounded-lg ${
                                isDataUpToDate
                                    ? 'bg-green-50 border border-green-100 text-green-700'
                                    : 'bg-yellow-50 border border-yellow-100 text-yellow-700'
                            }`}
                        >
                            {isDataUpToDate ? (
                                <CheckCircle className="w-6 h-6"/>
                            ) : (
                                <AlertTriangle className="w-6 h-6"/>
                            )}
                            <div>
                                <p className="font-bold">
                                    {isDataUpToDate ? 'Data is Up-to-Date' : 'Warning'}
                                </p>
                                <p>
                                    {isDataUpToDate
                                        ? 'The data is current as of yesterday.'
                                        : 'The data is not up-to-date and may be outdated.'}
                                </p>
                            </div>
                        </div>
                    )}
                    {/* Search and Generate Section */}
                    <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4">
                        <div className="relative flex-grow">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Search className="h-5 w-5 text-gray-400 dark:text-gray-500"/>
                            </div>
                            <input
                                type="text"
                                placeholder="Search properties..."
                                className="pl-10 pr-4 py-3 w-full border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <button
                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-white transition-all duration-200 ${
                                isGenerating || selectedProperties.length === 0
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-blue-600 hover:bg-blue-700 shadow-lg hover:shadow-xl'
                            }`}
                            onClick={handleGenerateReports}
                            disabled={selectedProperties.length === 0 || isGenerating}
                        >
                            {isGenerating ? (
                                <>
                                    <div
                                        className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"/>
                                    <span>Generating...</span>
                                </>
                            ) : (
                                <>
                                    <Download className="h-5 w-5"/>
                                    <span>Generate Reports {selectedProperties.length > 0 && `(${selectedProperties.length})`}</span>
                                </>
                            )}
                        </button>
                    </div>

                    {/* Properties Table */}
                    <div className="overflow-hidden rounded-lg border border-gray-200">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 dark:bg-gray-700">
                                <tr className="bg-gray-50">
                                    <th className="px-6 py-4 text-left">
                                        <input
                                            type="checkbox"
                                            checked={selectedProperties.length === properties.length && properties.length > 0}
                                            onChange={() => {
                                                if (selectedProperties.length === properties.length) {
                                                    setSelectedProperties([]);
                                                } else {
                                                    setSelectedProperties(properties.map(p => p.PropertyKey));
                                                }
                                            }}
                                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        />
                                    </th>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600">Property
                                        Name
                                    </th>
                                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-600">Property
                                        ID
                                    </th>
                                </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan="3" className="px-6 py-8 text-center text-gray-500">
                                            <div className="flex items-center justify-center gap-2">
                                                <div
                                                    className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full"/>
                                                <span>Loading properties...</span>
                                            </div>
                                        </td>
                                    </tr>
                                ) : properties.length === 0 ? (
                                    <tr>
                                        <td colSpan="3"
                                            className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                                            No properties found
                                        </td>
                                    </tr>
                                ) : (
                                    properties.map((property) => (
                                        <tr
                                            key={property.PropertyKey}
                                            className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                                            onClick={() => togglePropertySelection(property.PropertyKey)}
                                        >
                                            <td className="px-6 py-4">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedProperties.includes(property.PropertyKey)}
                                                    onChange={() => togglePropertySelection(property.PropertyKey)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                />
                                            </td>
                                            <td className="px-6 py-4 text-gray-900 dark:text-gray-100">{property.PropertyName}</td>
                                            <td className="px-6 py-4 text-gray-600 dark:text-gray-300">{property.PropertyKey}</td>
                                        </tr>
                                    ))
                                )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Selection Counter */}
                    <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-300">
                        <span>{selectedProperties.length} of {properties.length} properties selected</span>
                    </div>
                </CardContent>
            </Card>
            {/* Download Manager */}
            {downloadManagerState.files.length > 0 && (
                <DownloadManager
                    files={downloadManagerState.files}
                    isVisible={downloadManagerState.isVisible}
                    onDownload={handleDownload}
                    onDownloadAll={handleDownloadAll}
                    onClose={hideDownloadManager}
                    downloadProgress={downloadProgress}  // Add the downloadProgress prop
                />
            )}

            {/* Floating Download Button */}
            {downloadManagerState.showFloatingButton &&
                !downloadManagerState.isVisible &&
                downloadManagerState.files.length > 0 && (
                    <div className="fixed bottom-4 right-4">
                    <FloatingDownloadButton
                        filesCount={downloadManagerState.files.length}
                        completedCount={downloadManagerState.files.filter(f => f.downloaded).length}
                        onClick={handleFloatingButtonClick}
                    />
                    </div>
                )}

        </div>
    );
};

export default PropertyReportGenerator;