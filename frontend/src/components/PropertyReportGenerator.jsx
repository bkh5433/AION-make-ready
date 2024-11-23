import React, {useState, useEffect, useRef} from 'react';
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

    const searchInputRef = useRef(null);

    const [showScrollTop, setShowScrollTop] = useState(false);

    useEffect(() => {
        const handleKeyPress = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInputRef.current?.focus();
            }
        };

        document.addEventListener('keydown', handleKeyPress);
        return () => document.removeEventListener('keydown', handleKeyPress);
    }, []);

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

    useEffect(() => {
        const handleScroll = () => {
            setShowScrollTop(window.scrollY > 400);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="container mx-auto space-y-8 px-4 py-6 max-w-7xl">
            {/* Notifications Container - Add scale transition */}
            <div className="fixed top-4 right-4 z-50 space-y-3">
                {notifications.map(notification => (
                    <div
                        key={notification.id}
                        className={`flex items-center gap-2 p-4 rounded-lg shadow-lg slide-in-from-right transform transition-all duration-200 hover:translate-x-[-4px] ${
                            notification.type === 'success'
                                ? 'bg-green-500/90 text-white'
                                : notification.type === 'error'
                                    ? 'bg-red-500/90 text-white'
                                    : 'bg-blue-500/90 text-white'
                        }`}
                    >
                        {notification.type === 'success' && <CheckCircle className="h-5 w-5"/>}
                        {notification.type === 'error' && <X className="h-5 w-5"/>}
                        {notification.type === 'info' && <AlertTriangle className="h-5 w-5"/>}
                        <p>{notification.message}</p>
                        <button
                            onClick={() => removeNotification(notification.id)}
                            className="ml-2 hover:opacity-80"
                        >
                            <X className="h-4 w-4"/>
                        </button>
                    </div>
                ))}
            </div>

            <Card
                className="bg-white dark:bg-[#1f2937] shadow-xl border border-gray-200 dark:border-gray-700 transition-all duration-200">
                <CardContent className="space-y-8 pt-6">
                    {/* Data Age Status Message - Add hover effect */}
                    {isDataUpToDate !== null && (
                        <div
                            className={`flex items-center gap-3 p-4 rounded-lg transition-all duration-200 hover:shadow-md ${
                                isDataUpToDate
                                    ? 'bg-green-50 dark:bg-green-50/10 border border-green-200 dark:border-green-100/20 text-green-700 dark:text-green-400'
                                    : 'bg-yellow-50 dark:bg-yellow-50/10 border border-yellow-200 dark:border-yellow-100/20 text-yellow-700 dark:text-yellow-400'
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

                    {/* Search and Generate Section - Improve spacing and button feedback */}
                    <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-6">
                        <div className="relative flex-grow">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <Search className="h-5 w-5 text-gray-400"/>
                            </div>
                            <input
                                ref={searchInputRef}
                                type="text"
                                placeholder="Search properties..."
                                className="pl-10 pr-10 py-3 w-full rounded-lg bg-gray-50 dark:bg-[#2d3748] border-gray-200 dark:border-gray-700 
                                text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 
                                focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200
                                hover:border-gray-300 dark:hover:border-gray-600"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                            {searchTerm && (
                                <button
                                    onClick={() => setSearchTerm('')}
                                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                >
                                    <X className="h-5 w-5"/>
                                </button>
                            )}
                        </div>
                        <button
                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-white transition-all duration-200 
                            transform hover:scale-[1.02] active:scale-[0.98] ${
                                isGenerating || selectedProperties.length === 0
                                    ? 'bg-gray-400 dark:bg-gray-600 cursor-not-allowed opacity-75'
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

                    {/* Properties Table - Add better hover states and transitions */}
                    <div
                        className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-600">
                        <table className="w-full">
                            <thead>
                            <tr className="bg-gray-50 dark:bg-[#2d3748]">
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
                                            className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-blue-600 focus:ring-blue-500"
                                        />
                                    </th>
                                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-400">Property
                                        Name
                                    </th>
                                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-gray-400">Property
                                        ID
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan="3" className="px-6 py-4">
                                            <div className="space-y-3">
                                                {[...Array(5)].map((_, i) => (
                                                    <div key={i} className="flex items-center gap-4 animate-pulse">
                                                        <div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        <div className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                    </div>
                                                ))}
                                            </div>
                                        </td>
                                    </tr>
                                ) : properties.length === 0 ? (
                                    <tr>
                                        <td colSpan="3" className="px-6 py-12 text-center">
                                            <div className="flex flex-col items-center justify-center gap-2">
                                                <Search className="h-8 w-8 text-gray-400"/>
                                                <span
                                                    className="text-gray-500 dark:text-gray-400">No properties found</span>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    properties.map((property) => (
                                        <tr
                                            key={property.PropertyKey}
                                            className="hover:bg-gray-50 dark:hover:bg-[#374151] cursor-pointer transition-all duration-200"
                                            onClick={() => togglePropertySelection(property.PropertyKey)}
                                        >
                                            <td className="px-6 py-4">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedProperties.includes(property.PropertyKey)}
                                                    onChange={() => togglePropertySelection(property.PropertyKey)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-blue-600 focus:ring-blue-500"
                                                />
                                            </td>
                                            <td className="px-6 py-4 text-gray-900 dark:text-gray-100">
                                                <div className="group relative">
                                                    <span
                                                        className="truncate block max-w-md">{property.PropertyName}</span>
                                                    <span
                                                        className="invisible group-hover:visible absolute left-0 top-full mt-2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-sm rounded-md z-10 whitespace-nowrap">
                                                        {property.PropertyName}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-gray-600 dark:text-gray-300">{property.PropertyKey}</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Selection Counter - Add better visibility */}
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-400 flex items-center gap-2">
                        <span className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded">
                            {selectedProperties.length}
                        </span>
                        of {properties.length} properties selected
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

            {showScrollTop && (
                <button
                    onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}
                    className="fixed bottom-4 left-4 p-2 bg-gray-100 dark:bg-gray-800 rounded-full shadow-lg 
                             hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200
                             transform hover:scale-110"
                    aria-label="Scroll to top"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M5 10l7-7m0 0l7 7m-7-7v18"/>
                    </svg>
                </button>
            )}

        </div>
    );
};

export default PropertyReportGenerator;