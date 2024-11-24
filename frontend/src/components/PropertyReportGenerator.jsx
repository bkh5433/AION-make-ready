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
import {Tooltip} from './ui/tooltip';

// Add this helper function at the top of the file, outside the component
const parseAPIDate = (dateStr) => {
    if (!dateStr) return null;

    // First try parsing as ISO string
    let date = new Date(dateStr);
    if (!isNaN(date.getTime())) {
        return date;
    }

    // Try parsing YYYY-MM-DD format
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return new Date(dateStr + 'T00:00:00Z');
    }

    // Try parsing the SQL format (YYYY-MM-DD HH:mm:ss)
    const sqlMatch = dateStr.match(/^(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2})$/);
    if (sqlMatch) {
        return new Date(sqlMatch[1] + 'T' + sqlMatch[2] + 'Z');
    }

    console.warn('Unable to parse date:', dateStr);
    return null;
};

const getWorkOrderSeverity = (openWorkOrders, unitCount) => {
    // Calculate work orders per unit
    const workOrdersPerUnit = openWorkOrders / unitCount;

    // Define thresholds based on work orders per unit
    if (workOrdersPerUnit >= 0.5) {
        return {
            color: 'text-red-600 dark:text-red-400',
            severity: 'high',
            message: 'High volume'
        };
    } else if (workOrdersPerUnit >= 0.25) {
        return {
            color: 'text-yellow-600 dark:text-yellow-400',
            severity: 'medium',
            message: 'Moderate'
        };
    } else {
        return {
            color: 'text-green-600 dark:text-green-400',
            severity: 'low',
            message: 'Normal'
        };
    }
};

// Add this helper function near the other helper functions at the top
const getPendingSeverity = (pendingWorkOrders, unitCount) => {
    // Calculate pending work orders per unit
    const pendingPerUnit = pendingWorkOrders / unitCount;

    if (pendingPerUnit >= 0.25) {
        return {
            color: 'text-orange-600 dark:text-orange-400',
            bgColor: 'bg-orange-100 dark:bg-orange-900/30',
            borderColor: 'border-orange-200 dark:border-orange-800',
            severity: 'high',
            message: 'High pending'
        };
    } else if (pendingPerUnit >= 0.1) {
        return {
            color: 'text-amber-600 dark:text-amber-400',
            bgColor: 'bg-amber-100 dark:bg-amber-900/30',
            borderColor: 'border-amber-200 dark:border-amber-800',
            severity: 'medium',
            message: 'Moderate'
        };
    } else {
        return {
            color: 'text-gray-600 dark:text-gray-400',
            bgColor: 'bg-gray-100 dark:bg-gray-800',
            borderColor: 'border-gray-200 dark:border-gray-700',
            severity: 'low',
            message: 'Normal'
        };
    }
};

// Update the TOOLTIP_CONTENT to be a function that takes property data
const getTooltipContent = (property) => ({
    workOrderSeverity: {
        high: `High volume: ${property.metrics.actual_open_work_orders} open work orders (${(property.metrics.actual_open_work_orders / property.unitCount).toFixed(2)} per unit)`,
        medium: `Moderate volume: ${property.metrics.actual_open_work_orders} open work orders (${(property.metrics.actual_open_work_orders / property.unitCount).toFixed(2)} per unit)`,
        low: `Normal volume: ${property.metrics.actual_open_work_orders} open work orders (${(property.metrics.actual_open_work_orders / property.unitCount).toFixed(2)} per unit)`
    },
    completionRate: {
        high: `Excellent: ${property.metrics.percentage_completed}% completion rate`,
        medium: `Good: ${property.metrics.percentage_completed}% completion rate`,
        low: `Needs attention: ${property.metrics.percentage_completed}% completion rate`
    },
    avgDays: `Average completion time per work order: ${property.metrics.average_days_to_complete.toFixed(1)} days`,
    pending: `${property.metrics.pending_work_orders} work orders pending start (${(property.metrics.pending_work_orders / property.unitCount).toFixed(2)} per unit)`,
    woPerUnit: `${property.metrics.actual_open_work_orders} open work orders across ${property.unitCount} units`,
    cancelled: `${property.metrics.cancelled_work_orders} work orders cancelled (${((property.metrics.cancelled_work_orders / property.metrics.actual_open_work_orders) * 100).toFixed(1)}% of total)`
});

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

    // Add new state variables to hold the period start and end dates
    const [periodStartDate, setPeriodStartDate] = useState(null);
    const [periodEndDate, setPeriodEndDate] = useState(null);

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

                    // Map properties with all necessary fields including dates
                    const formattedProperties = response.data.map(property => ({
                        PropertyKey: property.property_key,
                        PropertyName: property.property_name,
                        metrics: property.metrics,
                        status: property.status,
                        unitCount: property.total_unit_count,
                        period_start_date: property.period_start_date,
                        period_end_date: property.period_end_date,
                        latest_post_date: property.latest_post_date
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
    // console.log('Raw properties before filtering:', properties);

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

    useEffect(() => {
        if (properties.length > 0) {
            const firstProperty = properties[0];
            console.log('First property dates:', {
                start: firstProperty.period_start_date,
                end: firstProperty.period_end_date
            });

            const startDate = parseAPIDate(firstProperty.period_start_date);
            const endDate = parseAPIDate(firstProperty.period_end_date);

            if (startDate && endDate) {
                setPeriodStartDate(startDate);
                setPeriodEndDate(endDate);
                console.log('Period dates set:', {
                    start: startDate.toLocaleDateString(),
                    end: endDate.toLocaleDateString()
                });
            } else {
                console.warn('Invalid dates received:', {
                    start: firstProperty.period_start_date,
                    end: firstProperty.period_end_date
                });
            }
        }
    }, [properties]);

    // Update the date display in the JSX to handle potential null values
    const formatDate = (date) => {
        if (!date || isNaN(date.getTime())) return 'N/A';
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        }).format(date);
    };

    return (
        <div className="container mx-auto space-y-8 px-4 py-6 max-w-[90rem]">
            {/* Notifications Container - Add scale transition */}
            <div className="fixed top-4 right-4 z-50 space-y-3">
                {notifications.map(notification => (
                    <div
                        key={notification.id}
                        className={`flex items-center gap-2 p-4 rounded-lg shadow-lg slide-in-from-right transform transition-all duration-300 hover:translate-x-[-4px] hover:shadow-xl ${
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
                <CardContent className="space-y-10 p-8">
                    {/* Data Age Status Message - Add hover effect */}
                    {isDataUpToDate !== null && (
                        <div
                            className={`flex items-center gap-3 p-4 rounded-lg transition-all duration-300 animate-scale-in ${
                                isDataUpToDate
                                    ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700'
                                    : 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700'
                            }`}
                        >
                            <div className="flex-shrink-0">
                                {isDataUpToDate ? (
                                    <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400"/>
                                ) : (
                                    <AlertTriangle className="w-6 h-6 text-yellow-600 dark:text-yellow-400"/>
                                )}
                            </div>
                            <div className="flex-grow">
                                <div className="flex items-center gap-2">
                                    <h3 className={`font-semibold ${
                                        isDataUpToDate
                                            ? 'text-green-900 dark:text-green-100'
                                            : 'text-yellow-900 dark:text-yellow-100'
                                    }`}>
                                        {isDataUpToDate ? 'Data is Current (as of yesterday)' : 'Data Status Warning'}
                                    </h3>
                                    <span
                                        className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                                        {properties.length} Properties
                                    </span>
                                </div>
                                <div className="mt-1 space-y-1">
                                    <p className={`text-sm ${
                                        isDataUpToDate
                                            ? 'text-green-700 dark:text-green-300'
                                            : 'text-yellow-700 dark:text-yellow-300'
                                    }`}>
                                        {isDataUpToDate
                                            ? 'All property data is complete through yesterday and ready for report generation.'
                                            : 'Property data may be outdated. Reports may not reflect the most recent changes.'}
                                    </p>
                                    {periodStartDate && periodEndDate && (
                                        <div
                                            className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 dark:text-gray-400">
                                            <div className="flex items-center gap-1">
                                                <span className="font-medium">30-Day Period:</span>
                                                <span>
                                                    {formatDate(periodStartDate)}
                                                    {' - '}
                                                    {formatDate(periodEndDate)}
                                                    <span className="ml-1 text-xs text-gray-500">
                                                        (Data complete through end of day)
                                                    </span>
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Search and Generate Section - Improve spacing and button feedback */}
                    <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-6">
                        <div className="relative flex-grow animate-slide-up">
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
                            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-white 
                            transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] 
                            ${isGenerating ? 'animate-pulse-shadow' : ''} ${
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
                        className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1f2937]">
                        <table className="w-full">
                            <thead>
                            <tr className="bg-gray-50 dark:bg-[#2d3748] border-b border-gray-200 dark:border-gray-800">
                                <th className="px-8 py-5 text-left">
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
                                            className="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-500 focus:ring-blue-500"
                                        />
                                    </th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-400">Property
                                    Name
                                </th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-400">Units</th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-400">Completion
                                    Rate
                                </th>
                                <th className="hidden md:table-cell px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-400 min-w-[320px]">Work
                                    Orders
                                </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                                {isLoading ? (
                                    // Updated skeleton loading rows
                                    [...Array(5)].map((_, i) => (
                                        <tr key={i}>
                                            <td colSpan="5" className="px-8 py-8">
                                                <div className="flex items-start gap-8 animate-pulse"
                                                     style={{animationDelay: `${i * 100}ms`}}>
                                                    {/* Checkbox skeleton */}
                                                    <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded"/>

                                                    {/* Property info skeleton */}
                                                    <div className="flex-1 space-y-3">
                                                        <div className="space-y-2">
                                                            <div
                                                                className="h-5 w-64 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                            <div
                                                                className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        </div>
                                                    </div>

                                                    {/* Units skeleton */}
                                                    <div className="w-24 space-y-2">
                                                        <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                    </div>

                                                    {/* Completion rate skeleton */}
                                                    <div className="w-48 space-y-2">
                                                        <div className="flex items-center gap-2">
                                                            <div
                                                                className="h-2 w-24 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                                                            <div
                                                                className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        </div>
                                                        <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                    </div>

                                                    {/* Work orders skeleton */}
                                                    <div className="hidden md:block w-80 space-y-6">
                                                        {/* Open work orders */}
                                                        <div className="space-y-2">
                                                            <div
                                                                className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                            <div className="flex items-center gap-2">
                                                                <div
                                                                    className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                                <div
                                                                    className="h-6 w-24 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                                                            </div>
                                                            <div
                                                                className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        </div>

                                                        {/* Pending work orders */}
                                                        <div className="space-y-2">
                                                            <div
                                                                className="h-4 w-48 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                            <div className="flex items-center gap-2">
                                                                <div
                                                                    className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                                <div
                                                                    className="h-6 w-24 bg-gray-200 dark:bg-gray-700 rounded-full"/>
                                                            </div>
                                                            <div
                                                                className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded"/>
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                ) : properties.length === 0 ? (
                                    <tr>
                                        <td colSpan="5" className="px-8 py-16 text-center">
                                            <div className="flex flex-col items-center justify-center gap-2">
                                                <Search className="h-8 w-8 text-gray-400"/>
                                                <span
                                                    className="text-gray-500 dark:text-gray-400">No properties found</span>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    properties.map((property, index) => (
                                        <tr
                                            key={property.PropertyKey}
                                            className={`cursor-pointer transition-all duration-200 animate-slide-up
                                                        ${selectedProperties.includes(property.PropertyKey)
                                                ? 'bg-blue-50 dark:bg-blue-900/30'
                                                : 'hover:bg-gray-50 dark:hover:bg-[#2d3748]'}`}
                                            style={{animationDelay: `${index * 50}ms`}}
                                            onClick={() => togglePropertySelection(property.PropertyKey)}
                                        >
                                            <td className="px-8 py-6">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedProperties.includes(property.PropertyKey)}
                                                    onChange={() => togglePropertySelection(property.PropertyKey)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className={`rounded border-gray-600 
                                                                ${selectedProperties.includes(property.PropertyKey)
                                                        ? 'bg-blue-900/50 border-blue-400'
                                                        : 'bg-gray-700'} 
                                                                text-blue-400 focus:ring-blue-500`}
                                                />
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex flex-col">
                                                    <span
                                                        className="font-medium text-gray-900 dark:text-gray-100">{property.PropertyName}</span>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span
                                                            className="text-sm text-gray-500 dark:text-gray-400">ID: {property.PropertyKey}</span>
                                                        {property.metrics.average_days_to_complete > 5 && (
                                                            <Tooltip content={getTooltipContent(property).avgDays}>
                                                                <span
                                                                    className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
                                                                    Avg {property.metrics.average_days_to_complete.toFixed(1)} days
                                                                </span>
                                                            </Tooltip>
                                                        )}
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex flex-col">
                                                    <span className="font-medium">{property.unitCount}</span>
                                                    <Tooltip content={getTooltipContent(property).woPerUnit}>
                                                        <span className="text-xs text-gray-500 dark:text-gray-400">
                                                            {(property.metrics.actual_open_work_orders / property.unitCount).toFixed(2)} WO/unit
                                                        </span>
                                                    </Tooltip>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <Tooltip content={
                                                    getTooltipContent(property).completionRate[
                                                        property.metrics.percentage_completed >= 90
                                                            ? 'high'
                                                            : property.metrics.percentage_completed >= 75
                                                                ? 'medium'
                                                                : 'low'
                                                        ]
                                                }>
                                                    <div className="flex items-center gap-2">
                                                        <div
                                                            className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                                                            <div
                                                                className={`h-2 rounded-full transform origin-left ${
                                                                    property.metrics.percentage_completed >= 90 ? 'bg-green-500' :
                                                                        property.metrics.percentage_completed >= 75 ? 'bg-yellow-500' :
                                                                            'bg-red-500'
                                                                }`}
                                                                style={{
                                                                    transform: 'scaleX(0)',
                                                                    animation: 'progress-scale 0.6s ease-out forwards',
                                                                    animationDelay: `${index * 50}ms`,
                                                                    transformOrigin: 'left',
                                                                    width: `${property.metrics.percentage_completed}%`
                                                                }}
                                                            />
                                                        </div>
                                                        <span className={`text-sm font-medium ${
                                                            property.metrics.percentage_completed >= 90 ? 'text-green-600 dark:text-green-400' :
                                                                property.metrics.percentage_completed >= 75 ? 'text-yellow-600 dark:text-yellow-400' :
                                                                    'text-red-600 dark:text-red-400'
                                                        }`}>
                                                            {property.metrics.percentage_completed.toFixed(1)}%
                                                        </span>
                                                    </div>
                                                </Tooltip>
                                                <div
                                                    className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                                                    <span>{property.metrics.completed_work_orders} completed</span>
                                                    {property.metrics.cancelled_work_orders > 0 && (
                                                        <Tooltip content={getTooltipContent(property).cancelled}>
                                                            <span className="text-red-500 dark:text-red-400">
                                                                • {property.metrics.cancelled_work_orders} cancelled
                                                            </span>
                                                        </Tooltip>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="hidden md:table-cell px-8 py-6 min-w-[320px]">
                                                <div className="flex flex-col gap-4">
                                                    {/* Open Work Orders Section */}
                                                    <div className="flex flex-col">
                                                        <span
                                                            className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">
                                                            OPEN WORK ORDERS (TOTAL)
                                                        </span>
                                                        {(() => {
                                                            const severity = getWorkOrderSeverity(
                                                                property.metrics.actual_open_work_orders,
                                                                property.unitCount
                                                            );
                                                            return (
                                                                <>
                                                                    <div className="flex items-center gap-2">
                                                                        <span
                                                                            className={`text-lg font-medium ${severity.color}`}>
                                                                            {property.metrics.actual_open_work_orders}
                                                                        </span>
                                                                        <Tooltip
                                                                            content={getTooltipContent(property).workOrderSeverity[severity.severity]}>
                                                                            <span
                                                                                className={`text-xs inline-flex items-center px-3 py-1 rounded-full font-medium whitespace-nowrap ${
                                                                                severity.severity === 'high'
                                                                                    ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400 border border-red-200 dark:border-red-800'
                                                                                    : severity.severity === 'medium'
                                                                                        ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800'
                                                                                        : 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 border border-green-200 dark:border-green-800'
                                                                            }`}>
                                                                            {severity.message}
                                                                        </span>
                                                                        </Tooltip>
                                                                    </div>
                                                                    <span
                                                                        className="text-sm text-gray-500 dark:text-gray-400">
                                                                        {(property.metrics.actual_open_work_orders / property.unitCount).toFixed(2)} per unit
                                                                    </span>
                                                                </>
                                                            );
                                                        })()}
                                                    </div>

                                                    {/* Pending Work Orders Section */}
                                                    <div className="flex flex-col">
                                                        <span
                                                            className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1">
                                                            PENDING START (NOT YET ASSIGNED)
                                                        </span>
                                                        {(() => {
                                                            const pendingSeverity = getPendingSeverity(
                                                                property.metrics.pending_work_orders,
                                                                property.unitCount
                                                            );
                                                            return (
                                                                <>
                                                                    <div className="flex items-center gap-2">
                                                                        <span
                                                                            className={`text-lg font-medium ${pendingSeverity.color}`}>
                                                                            {property.metrics.pending_work_orders}
                                                                        </span>
                                                                        <Tooltip
                                                                            content={getTooltipContent(property).pending}>
                                                                            <span className={`text-xs inline-flex items-center px-3 py-1 rounded-full font-medium whitespace-nowrap 
                                                                                ${pendingSeverity.bgColor} ${pendingSeverity.color} border ${pendingSeverity.borderColor}`}>
                                                                                {pendingSeverity.message}
                                                                            </span>
                                                                        </Tooltip>
                                                                    </div>
                                                                    <span
                                                                        className="text-sm text-gray-500 dark:text-gray-400">
                                                                        {(property.metrics.pending_work_orders / property.unitCount).toFixed(2)} per unit
                                                                    </span>
                                                                </>
                                                            );
                                                        })()}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Selection Counter - Add better visibility */}
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-400 flex items-center gap-2 px-2">
                        <span className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded">
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