import React, {useState, useEffect, useRef, useCallback} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from './ui/card';
import {
    Search,
    Download,
    FileDown,
    CheckCircle,
    X,
    Plus,
    AlertTriangle,
    Moon,
    Sun,
    Info,
    AlertCircle,
    HelpCircle
} from 'lucide-react';
import {motion, AnimatePresence} from 'framer-motion';
import {useTheme} from "../lib/theme.jsx";
import {api} from '../lib/api';
import DownloadManager from './DownloadManager';
import FloatingDownloadButton from './FloatingDownloadButton';
import useSessionManager from '../lib/session';
import {getSessionId} from '../lib/session';
import {Tooltip} from './ui/tooltip';
import PropertyRow from './PropertyRow';
import {useAuth} from '../lib/auth';
import DataFreshnessIndicator from './DataFreshnessIndicator';
import {debounce} from '../lib/utils';
import {searchCache} from '../lib/cache';
import HelpOverlay from './ui/help-overlay';

// Add StatusBanner component
const StatusBanner = ({status, message, icon: Icon}) => (
    <motion.div
        key={status}
        initial={{opacity: 0, y: -20}}
        animate={{opacity: 1, y: 0}}
        exit={{opacity: 0, y: -20}}
        transition={{duration: 0.2}}
        className={`w-full py-2 px-4 text-sm text-center font-medium
            ${status === 'critical'
            ? 'bg-red-500/10 text-red-600 dark:text-red-500'
            : status === 'extended'
                ? 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-500'
                : 'bg-blue-500/10 text-blue-600 dark:text-blue-500'}`}
    >
        <motion.div
            initial={{opacity: 0}}
            animate={{opacity: 1}}
            transition={{duration: 0.2, delay: 0.1}}
            className="flex items-center justify-center gap-2 max-w-2xl mx-auto"
        >
            <Icon className="h-4 w-4"/>
            <span>{message}</span>
        </motion.div>
    </motion.div>
);

const parseAPIDate = (dateStr) => {
    if (!dateStr) return null;

    // First try parsing as ISO string (API returns UTC dates)
    let date = new Date(dateStr);
    if (!isNaN(date.getTime())) {
        return date;
    }

    // Try parsing YYYY-MM-DD format (as UTC)
    if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return new Date(dateStr + 'T00:00:00Z');
    }

    // Try parsing the SQL format (YYYY-MM-DD HH:mm:ss) as UTC
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
const getTooltipContent = (property) => {
    // Calculate total work orders handled during the period
    const totalWorkOrders = property.metrics.open_work_order_current + property.metrics.actual_open_work_orders_current;

    return {
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
        cancelled: `${property.metrics.cancelled_work_orders} work orders cancelled (${
            totalWorkOrders > 0
                ? ((property.metrics.cancelled_work_orders / totalWorkOrders) * 100).toFixed(1)
                : 0
        }% of total)`
    };
};

// Function to generate dynamic search examples from properties data
const generateSearchExamples = (propertiesData) => {
    if (!propertiesData || propertiesData.length === 0) {
        return [
            "Search properties",
            "Philadelphia",

        ];
    }

    const examples = ["Search properties"];
    const states = new Set();
    const propertyNames = new Set();

    // Collect unique states and property names
    propertiesData.forEach(property => {
        if (property.property_state_province_code) {
            states.add(property.property_state_province_code);
        }
        if (property.property_name) {
            propertyNames.add(property.property_name);
        }
    });

    // Add 2 random property names if available
    const propertyNamesArray = Array.from(propertyNames);
    for (let i = 0; i < 2 && propertyNamesArray.length > 0; i++) {
        const randomIndex = Math.floor(Math.random() * propertyNamesArray.length);
        examples.push(propertyNamesArray[randomIndex]);
        propertyNamesArray.splice(randomIndex, 1);
    }

    // Add 2 random states if available
    const statesArray = Array.from(states);
    for (let i = 0; i < 2 && statesArray.length > 0; i++) {
        const randomIndex = Math.floor(Math.random() * statesArray.length);
        examples.push(statesArray[randomIndex]);
        statesArray.splice(randomIndex, 1);
    }

    // Add debug logging
    console.log('Generated search examples:', examples);
    console.log('From properties:', propertiesData.slice(0, 2));

    return examples;
};

const PropertyReportGenerator = () => {
    const [rawProperties, setRawProperties] = useState([]); // New state for raw API data
    const [properties, setProperties] = useState([]);
    const [searchExamples, setSearchExamples] = useState([
        "Search properties",
        "Philadelphia",
    ]);
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

    // Add state for remote info message
    const [remoteInfo, setRemoteInfo] = useState(null);

    // Add effect to fetch remote info
    useEffect(() => {
        const fetchRemoteInfo = async () => {
            try {
                const response = await api.getRemoteInfo();
                if (response.success && response.info) {
                    setRemoteInfo({
                        message: response.info.message,
                        status: response.info.status || 'info',
                        icon: response.info.status === 'critical' ? AlertTriangle :
                            response.info.status === 'extended' ? AlertTriangle : Info
                    });
                }
            } catch (error) {
                console.error('Error fetching remote info:', error);
            }
        };

        fetchRemoteInfo();
        // Fetch every 5 minutes
        const interval = setInterval(fetchRemoteInfo, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const [downloadManagerState, setDownloadManagerState] = useState({
        isVisible: false,
        showFloatingButton: false,
        files: []
    });
    const [isFirstLoad, setIsFirstLoad] = useState(true); // Keep this state declaration where it is

    const searchInputRef = useRef(null);
    // Add a ref to track first load
    const isFirstLoadRef = useRef(true);

    const [showScrollTop, setShowScrollTop] = useState(false);
    const [isScrollTopVisible, setIsScrollTopVisible] = useState(false);
    const scrollTopTimeout = useRef(null);

    // Add new state variables to hold the period start and end dates
    const [periodStartDate, setPeriodStartDate] = useState(null);
    const [periodEndDate, setPeriodEndDate] = useState(null);

    const {user} = useAuth();
    const [isRefreshing, setIsRefreshing] = useState(false);

    const [prevSearchTerm, setPrevSearchTerm] = useState('');

    const [dataIssues, setDataIssues] = useState([]);

    const [isCachedResult, setIsCachedResult] = useState(false);

    const [confidenceScore, setConfidenceScore] = useState(1.0);

    const [currentTask, setCurrentTask] = useState(null);
    const [pollingIntervals, setPollingIntervals] = useState({});
    const [taskStartedAt, setTaskStartedAt] = useState(null);

    // Add isCompleted state
    const [isCompleted, setIsCompleted] = useState(false);

    // Replace single completion ref with a map of task completions
    const completedTasksRef = useRef(new Set());

    // Cleanup effect for polling intervals
    useEffect(() => {
        return () => {
            // Clear all polling intervals on unmount
            Object.values(pollingIntervals).forEach(interval => {
                if (interval) clearInterval(interval);
            });
        };
    }, [pollingIntervals]);

    const [currentPlaceholder, setCurrentPlaceholder] = useState(searchExamples[0]);
    const [isSearchFocused, setIsSearchFocused] = useState(false);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [nextPlaceholder, setNextPlaceholder] = useState('');

    // Add ref for previous examples
    const prevExamplesRef = useRef([]);

    // Update searchExamples when raw properties are loaded
    useEffect(() => {
        if (rawProperties.length > 0) {
            const examples = generateSearchExamples(rawProperties);
            // Compare with previous examples using ref
            if (JSON.stringify(examples) !== JSON.stringify(prevExamplesRef.current)) {
                setSearchExamples(examples);
                prevExamplesRef.current = examples;
            }
        }
    }, [rawProperties]); // Remove searchExamples from dependencies

    // Enhanced animation effect
    useEffect(() => {
        if (isSearchFocused || searchTerm) return;

        let currentIndex = 0;
        const cycleInterval = setInterval(() => {
            currentIndex = (currentIndex + 1) % searchExamples.length;

            // First, clear the current placeholder and start fade out
            setCurrentPlaceholder('');

            // Wait for fade out to complete before showing next placeholder
            setTimeout(() => {
                setIsTransitioning(true);
                setNextPlaceholder(searchExamples[currentIndex]);

                // After overlay animation completes, update the placeholder
                setTimeout(() => {
                    setCurrentPlaceholder(searchExamples[currentIndex]);
                    setIsTransitioning(false);
                }, 300);
            }, 300);

        }, 5000);

        return () => clearInterval(cycleInterval);
    }, [isSearchFocused, searchTerm, searchExamples]);

    const checkDataAge = (data) => {
        if (data.length > 0) {
            const firstItem = data[0];
            const latestPostDateStr = firstItem.latest_post_date;
            console.log('Latest Post Date String:', latestPostDateStr);

            const latestPostDate = parseAPIDate(latestPostDateStr);
            console.log('Parsed Latest Post Date:', latestPostDate);

            if (!latestPostDate) {
                throw new Error('Invalid latest_post_date format');
            }

            // Get yesterday's date at midnight UTC
            const now = new Date();
            const yesterday = new Date(Date.UTC(
                now.getUTCFullYear(),
                now.getUTCMonth(),
                now.getUTCDate() - 1
            ));
            console.log('Yesterday\'s Date:', yesterday);

            const isUpToDate = latestPostDate.getTime() === yesterday.getTime();
            setIsDataUpToDate(isUpToDate);
            console.log('Data is up-to-date:', isUpToDate);
        } else {
            setIsDataUpToDate(null);
            console.log('No data available');
        }
    };

    // Memoized debounced search function
    const debouncedSearch = useCallback(
        debounce(async (term, page = 1, perPage = 20) => {
            // Skip if this is the same search term and not the first load
            if (!isFirstLoadRef.current && term === prevSearchTerm) {
                return;
            }

            try {
                setIsLoading(true);
                setError(null);

                const response = await api.searchProperties(term, page, perPage);
                console.log('API Response:', response);

                if (!Array.isArray(response.data)) {
                    throw new Error('Invalid response format');
                }

                // Handle data issues if present
                if (response.data_issues && response.data_issues.length > 0) {
                    setDataIssues(response.data_issues);
                } else {
                    setDataIssues([]);
                }

                // Set confidence score from API response
                if (response.confidence_score !== undefined) {
                    setConfidenceScore(response.confidence_score);
                }

                // Use the function for response data
                checkDataAge(response.data);

                // Set the raw API response data for search examples
                setRawProperties(response.data);

                // Map properties for display
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

                setProperties(formattedProperties);
                setIsLoading(false);

                // Only show success notification on first load
                if (isFirstLoadRef.current) {
                    addNotification('success', 'Successfully fetched properties');
                    isFirstLoadRef.current = false;
                    setIsFirstLoad(false);
                }

                setPrevSearchTerm(term);

            } catch (error) {
                console.error(`Error fetching properties:`, error);
                setError('Unable to connect to the server. Please refresh the page and try again.');
                setRawProperties([]); // Clear raw properties
                setProperties([]); // Clear formatted properties
                setIsLoading(false);
                addNotification('error', 'Connection failed. Please refresh the page and try again.');
            }
        }, 750),
        [prevSearchTerm, isFirstLoadRef]
    );

    // Update the search effect to always trigger the search
    useEffect(() => {
        debouncedSearch(searchTerm);

        // Cleanup function to cancel pending searches
        return () => debouncedSearch.cancel();
    }, [searchTerm, debouncedSearch]);

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

    const checkReportStatus = async (taskId) => {
        // Don't proceed if this specific task is already completed
        if (completedTasksRef.current.has(taskId)) {
            return;
        }

        try {
            const result = await api.checkReportStatus(taskId);

            if (result.success) {
                // Update started_at state
                setTaskStartedAt(result.started_at);

                if (result.status === 'completed') {
                    // Mark this specific task as completed
                    completedTasksRef.current.add(taskId);

                    // Clear the specific interval for this task
                    if (pollingIntervals[taskId]) {
                        clearInterval(pollingIntervals[taskId]);
                        setPollingIntervals(prev => {
                            const updated = {...prev};
                            delete updated[taskId];
                            return updated;
                        });
                    }

                    setIsGenerating(false);
                    setCurrentTask(null);
                    setTaskStartedAt(null); // Reset started_at when task completes

                    // Show success notification and handle files
                    setNotifications([]);
                    addNotification('success', 'Reports generated successfully!');
                    setSelectedProperties([]);

                    if (result.files?.length) {
                        showDownloadManager(result.files, result.directory || 'output');
                    }
                } else if (result.status === 'failed') {
                    // Mark this specific task as completed
                    completedTasksRef.current.add(taskId);

                    // Clear the specific interval for this task
                    if (pollingIntervals[taskId]) {
                        clearInterval(pollingIntervals[taskId]);
                        setPollingIntervals(prev => {
                            const updated = {...prev};
                            delete updated[taskId];
                            return updated;
                        });
                    }

                    setIsGenerating(false);
                    setCurrentTask(null);
                    setTaskStartedAt(null); // Reset started_at when task fails
                    throw new Error(result.error || 'Report generation failed');
                }
                // Continue polling only if status is 'processing'
            } else {
                throw new Error(result.message || 'Failed to check report status');
            }
        } catch (error) {
            // Mark this specific task as completed
            completedTasksRef.current.add(taskId);

            // Clear the specific interval for this task
            if (pollingIntervals[taskId]) {
                clearInterval(pollingIntervals[taskId]);
                setPollingIntervals(prev => {
                    const updated = {...prev};
                    delete updated[taskId];
                    return updated;
                });
            }

            setIsGenerating(false);
            setCurrentTask(null);
            setTaskStartedAt(null); // Reset started_at when error occurs
            console.error('Error checking report status:', error);
            addNotification('error', `Error checking report status: ${error.message}`);
        }
    };

    const handleGenerateReports = async () => {
        if (selectedProperties.length === 0) {
            addNotification('error', 'Please select at least one property.');
            return;
        }

        setIsGenerating(true);
        setTaskStartedAt(null); // Reset started_at when starting new generation
        addNotification('info', `Generating reports for ${selectedProperties.length} properties...`);

        try {
            const result = await api.generateReports(selectedProperties);
            console.log('Generate reports response:', result);

            if (result.success) {
                if (result.session_id) {
                    updateSessionId(result.session_id);
                    console.log('Session ID set after report generation:', result.session_id);
                }

                if (!result.task_id) {
                    console.error('No task_id received from server');
                    throw new Error('No task ID received from server');
                }

                console.log('Setting current task:', result.task_id);
                setCurrentTask(result.task_id);

                // Start polling for this specific task
                if (!pollingIntervals[result.task_id]) {
                    console.log('Starting polling for task:', result.task_id);
                    const interval = setInterval(() => checkReportStatus(result.task_id), 2000);
                    setPollingIntervals(prev => ({
                        ...prev,
                        [result.task_id]: interval
                    }));
                }

                // Update notification to show processing status
                setNotifications([]);
                addNotification('info', 'Processing report...', 0);

                // Handle any warnings or data issues
                if (result.warnings?.length) {
                    result.warnings.forEach(warning => {
                        addNotification('warning', warning);
                    });
                }

                if (result.data_issues?.length) {
                    setDataIssues(result.data_issues);
                }
            } else {
                throw new Error(result.message || 'Failed to generate reports');
            }
        } catch (error) {
            setIsGenerating(false);
            console.error('Error generating reports:', error);
            addNotification('error', `Failed to generate reports: ${error.message}`);
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
            showFloatingButton: prev.files.some(f => f.downloaded)
        }));
    };

// Update showDownloadManager function
    const showDownloadManager = (files, outputDirectory) => {
        // Process files to ensure correct paths without duplication
        const processedFiles = files.map(file => {
            // Ensure we're working with a string
            let normalizedPath = typeof file === 'string' ? file : file.path || '';

            // Remove any duplicate 'output/' prefixes
            normalizedPath = normalizedPath.replace(/^(output\/)+/, '');

            // Build the correct file path with single output prefix
            const fullPath = normalizedPath;

            return {
                name: normalizedPath.split('/').pop(), // Get just the filename
                path: fullPath,
                downloaded: false,
                downloading: false,
                failed: false,
                timestamp: new Date().toISOString(),
                outputDirectory
            };
        });

        console.log('Adding new files to download manager:', processedFiles);

        // Merge new files with existing files, avoiding duplicates by path
        setDownloadManagerState(prev => {
            const existingPaths = new Set(prev.files.map(f => f.path));
            const newFiles = processedFiles.filter(f => !existingPaths.has(f.path));

            return {
                isVisible: true,
                showFloatingButton: true,
                files: [...prev.files, ...newFiles].sort((a, b) =>
                    new Date(b.timestamp) - new Date(a.timestamp)
                )
            };
        });
    };

// Update handleFloatingButtonClick function
    const handleFloatingButtonClick = () => {
        setDownloadManagerState(prev => ({
            ...prev,
            isVisible: true
        }));
    };

    const handleDownload = async (file) => {
        try {
            setDownloadProgress({
                type: 'progress',
                message: 'Downloading file...',
                completed: 0,
                total: 1
            });

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

            // Update file status
            setDownloadManagerState(prev => ({
                ...prev,
                files: prev.files.map(f =>
                    f.path === file.path ? {...f, downloaded: true} : f
                )
            }));

            setDownloadProgress(null);
        } catch (error) {
            console.error('Error downloading file:', error);
            setError('Failed to download file. Please try again.');
            setDownloadProgress(null);
        }
    };

    useEffect(() => {
        const handleScroll = () => {
            if (window.scrollY > 400) {
                setShowScrollTop(true);
                setIsScrollTopVisible(true);
            } else {
                setShowScrollTop(false);
                // Keep the component mounted but start exit animation
                if (isScrollTopVisible) {
                    if (scrollTopTimeout.current) {
                        clearTimeout(scrollTopTimeout.current);
                    }
                    scrollTopTimeout.current = setTimeout(() => {
                        setIsScrollTopVisible(false);
                    }, 500); // Match this with animation duration
                }
            }
        };

        window.addEventListener('scroll', handleScroll);
        return () => {
            window.removeEventListener('scroll', handleScroll);
            if (scrollTopTimeout.current) {
                clearTimeout(scrollTopTimeout.current);
            }
        };
    }, [isScrollTopVisible]);

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

    // Add cache invalidation on force refresh
    const handleForceRefresh = async () => {
        if (!user?.role === 'admin' || isRefreshing) return;

        // Clear the search cache before refreshing
        searchCache.clear();
        
        setIsRefreshing(true);
        try {
            const response = await api.forceRefreshData();
            if (response.status === 'success') {
                addNotification('info', 'Refresh initiated, this may take a few moments...');

                // Wait for initial cache update
                await new Promise(resolve => setTimeout(resolve, 5000));

                // Show success message before reload
                addNotification('success', 'Data refresh complete. Reloading page...');

                // Wait a moment for the notification to be visible
                await new Promise(resolve => setTimeout(resolve, 1500));

                // Reload the page
                window.location.reload();
            } else {
                throw new Error(response.message || 'Failed to refresh data');
            }
        } catch (error) {
            console.error('Error forcing refresh:', error);
            addNotification('error', `Failed to refresh data: ${error.message}`);
            setIsRefreshing(false);
        }
    };

    // Add effect to clear cache when component unmounts
    useEffect(() => {
        return () => {
            // Clear the search cache when component unmounts
            searchCache.clear();
        };
    }, []);

    // Update the DataIssuesAlert component
    const DataIssuesAlert = () => {
        if (dataIssues.length === 0) return null;

        return (
            <div className="px-8 py-2">
                <details className="text-sm group">
                    <summary
                        className="flex items-center gap-2 cursor-pointer text-yellow-600 dark:text-yellow-500 hover:text-yellow-700 dark:hover:text-yellow-400">
                        <AlertTriangle className="h-4 w-4"/>
                        <span className="font-medium">
                            {dataIssues.length} {dataIssues.length === 1 ? 'property has' : 'properties have'} data quality issues and cannot be displayed
                        </span>
                        <div className="ml-auto transform transition-transform duration-200 group-open:rotate-180">
                            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
                            </svg>
                        </div>
                    </summary>
                    <div className="mt-2 pl-6 text-sm text-gray-600 dark:text-gray-400">
                        <ul className="space-y-1">
                            {dataIssues.map((issue, index) => (
                                <li key={index} className="flex items-start gap-2">
                                    <span className="text-yellow-500 dark:text-yellow-400">•</span>
                                    <span>
                                        <span className="font-medium">{issue.property_name}</span>: {issue.message}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </details>
            </div>
        );
    };

    // Add this function to your component
    const handleClearCache = () => {
        searchCache.clear();
        addNotification('info', 'Search cache cleared');
        // Optionally refresh the current search
        if (searchTerm) {
            debouncedSearch(searchTerm);
        }
    };

    // Add state for help overlay near other state declarations
    const [showHelp, setShowHelp] = useState(false);

    // Add useEffect to show help on first visit
    useEffect(() => {
        const hasSeenHelp = localStorage.getItem('hasSeenHelp');
        if (!hasSeenHelp) {
            setShowHelp(true);
            localStorage.setItem('hasSeenHelp', 'true');
        }
    }, []);

    return (
        <div className="container mx-auto space-y-8 px-4 py-6 max-w-[90rem]">
            {/* Add Help Overlay */}
            <HelpOverlay isVisible={showHelp} onClose={() => setShowHelp(false)}/>

            {/* Add Help Button in the top-right corner */}
            <button
                onClick={() => setShowHelp(true)}
                className="fixed top-4 right-4 z-40 p-2 bg-white dark:bg-gray-800 rounded-full shadow-lg 
                    hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200
                    transform hover:scale-110"
                aria-label="Show help"
            >
                <HelpCircle className="h-5 w-5 text-gray-600 dark:text-gray-400"/>
            </button>

            {/* Notifications Container */}
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

            {/* Remote Info Banner */}
            <AnimatePresence mode="wait">
                {remoteInfo && (
                    <StatusBanner
                        status={remoteInfo.status}
                        message={remoteInfo.message}
                        icon={remoteInfo.icon}
                    />
                )}
            </AnimatePresence>

            <Card
                className="bg-white dark:bg-[#1f2937] shadow-xl border border-gray-200 dark:border-gray-700 transition-all duration-200 overflow-hidden">
                <CardContent className="space-y-10 p-0">
                    {/* Data Age Status Message */}
                    {isDataUpToDate !== null ? (
                        <DataFreshnessIndicator
                            isDataUpToDate={isDataUpToDate}
                            properties={properties}
                            periodStartDate={periodStartDate}
                            periodEndDate={periodEndDate}
                            onRefresh={handleForceRefresh}
                            isRefreshing={isRefreshing}
                            isAdmin={user?.role === 'admin'}
                            confidenceScore={confidenceScore}
                        />
                    ) : (
                        // Add a spacer div when the indicator is not visible
                        <div className="h-8"/> // This maintains top padding
                    )}

                    {/* Move DataIssuesAlert here, after DataFreshnessIndicator */}
                    <DataIssuesAlert/>

                    {/* Search and Generate Section */}
                    <div className="px-8 pb-8">
                        <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-6">
                            <div className="relative flex-grow animate-slide-up">
                                <div className={`relative transition-all duration-300
                                    ${isSearchFocused ? 'ring-1 ring-blue-500/10 shadow-md' : 'shadow-sm hover:shadow-sm'}
                                    rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm`}>
                                    <div
                                        className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        {isLoading ? (
                                            <div
                                                className="animate-spin h-5 w-5 border-2 border-gray-500 border-t-transparent rounded-full"/>
                                        ) : (
                                            <Search className={`h-5 w-5 transition-colors duration-300
                                                ${isSearchFocused ? 'text-blue-500' : 'text-gray-400'}`}/>
                                        )}
                                    </div>
                                    <div className="relative">
                                        <input
                                            ref={searchInputRef}
                                            type="text"
                                            className={`pl-10 pr-10 py-3 w-full rounded-lg
                                                bg-transparent
                                                border border-gray-200/50 dark:border-gray-700/50
                                                text-gray-900 dark:text-gray-100 
                                                placeholder-gray-500 dark:placeholder-gray-400
                                                focus:border-blue-500/10 focus:ring-0
                                                transition-all duration-300
                                                hover:border-gray-300/50 dark:hover:border-gray-600/50`}
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            onFocus={() => setIsSearchFocused(true)}
                                            onBlur={() => setIsSearchFocused(false)}
                                            placeholder={currentPlaceholder}
                                            aria-label="Search properties by name or location"
                                        />
                                        {/* Overlay for transition effect - only show when searchTerm is empty */}
                                        {isTransitioning && !isSearchFocused && !searchTerm && (
                                            <div
                                                className={`absolute inset-0 pointer-events-none
                                                    flex items-center pl-10 pr-10 text-gray-500 dark:text-gray-400
                                                    transition-opacity duration-300 ease-in-out
                                                    animate-placeholder-show`}
                                                aria-hidden="true"
                                            >
                                                {nextPlaceholder}
                                            </div>
                                        )}
                                    </div>
                                    {searchTerm && (
                                        <button
                                            onClick={() => setSearchTerm('')}
                                            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 
                                                hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-300"
                                        >
                                            <X className="h-5 w-5"/>
                                        </button>
                                    )}
                                </div>
                                {/* Search Results Count */}
                                {searchTerm && !isLoading && (
                                    <div className="absolute -bottom-6 left-0 text-xs text-gray-400 dark:text-gray-500">
                                        Found {properties.length} {properties.length === 1 ? 'match ' : 'matches '}
                                        for "{searchTerm}"
                                    </div>
                                )}
                            </div>
                            <button
                                className={`flex flex-col items-center justify-center gap-1 px-6 py-3 rounded-lg
                                transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]
                                shadow-lg hover:shadow-xl min-w-[200px]
                                ${isGenerating ? 'animate-pulse-shadow' : ''}
                                ${isGenerating || selectedProperties.length === 0
                                    ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-500 dark:hover:to-blue-600 text-white border border-blue-600/20 dark:border-blue-500/20 hover:border-blue-500/30 dark:hover:border-blue-400/30 backdrop-blur-sm'
                                }`}
                                onClick={handleGenerateReports}
                                disabled={selectedProperties.length === 0 || isGenerating}
                            >
                                {isGenerating ? (
                                    <>
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"/>
                                            <span>Generating Reports</span>
                                        </div>
                                        <span className="text-xs text-blue-100 dark:text-blue-200 font-normal">
                                            {currentTask ? (
                                                taskStartedAt ? 'Processing...' : 'Requested...'
                                            ) : 'Starting...'}
                                        </span>
                                    </>
                                ) : (
                                    <div className="flex items-center gap-2">
                                        <Download
                                            className={`h-5 w-5 ${selectedProperties.length === 0 ? 'opacity-50' : ''}`}/>
                                        <span
                                            className="font-medium">Generate Report{selectedProperties.length !== 1 && 's'} {selectedProperties.length > 0 && `(${selectedProperties.length})`}</span>
                                    </div>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Properties Table - Add better hover states and transitions */}
                    <div
                        className="relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 
                        bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm backdrop-saturate-150
                        before:absolute before:inset-0 before:bg-gradient-to-b before:from-white/50 before:to-transparent dark:before:from-gray-900/50
                        before:pointer-events-none">
                        <table className="w-full relative">
                            <thead>
                            <tr className="bg-gray-50/80 dark:bg-gray-800/80 border-b border-gray-200/80 dark:border-gray-700/80
                                    backdrop-blur-sm transition-colors duration-200">
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
                                            className="rounded border-gray-300 dark:border-gray-600 bg-white/80 dark:bg-gray-700/80 
                                            text-blue-600 dark:text-blue-400 focus:ring-blue-500/50 transition-colors duration-200
                                            hover:border-blue-400 dark:hover:border-blue-300"
                                        />
                                    </th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                                    Property Name
                                </th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                                    Units
                                </th>
                                <th className="px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                                    Completion Rate
                                </th>
                                <th className="hidden md:table-cell px-8 py-5 text-left text-sm font-medium text-gray-600 dark:text-gray-300 min-w-[320px]">
                                    Work Orders
                                </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200/80 dark:divide-gray-700/80">
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
                                        <PropertyRow
                                            key={property.PropertyKey}
                                            property={property}
                                            onSelect={togglePropertySelection}
                                            isSelected={selectedProperties.includes(property.PropertyKey)}
                                            animationDelay={index * 50}
                                        />
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Selection Counter with enhanced styling */}
                    <div
                        className="text-sm font-medium text-gray-600 dark:text-gray-400 flex items-center gap-2 px-4 py-2">
                        <span className="px-3.5 py-1.5 bg-gray-100/80 dark:bg-gray-800/80 rounded-full
                            border border-gray-200/50 dark:border-gray-700/50 backdrop-blur-sm">
                            {selectedProperties.length}
                        </span>
                        <span>of {properties.length} properties selected</span>
                    </div>
                </CardContent>
            </Card>
            {/* Download Manager */}
            {downloadManagerState.files.length > 0 && (
                <DownloadManager
                    files={downloadManagerState.files}
                    onDownload={handleDownload}
                    onClose={() => setDownloadManagerState(prev => ({...prev, isVisible: false}))}
                    isVisible={downloadManagerState.isVisible}
                    downloadProgress={downloadProgress}
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

            {isScrollTopVisible && (
                <button
                    onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}
                    className={`fixed ${downloadManagerState.showFloatingButton && !downloadManagerState.isVisible ? 'bottom-20' : 'bottom-4'} right-4 
                             p-2 bg-gray-100 dark:bg-gray-800 rounded-full shadow-lg 
                             hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200
                             transform hover:scale-110 ${showScrollTop ? 'animate-bounce-in' : 'animate-bounce-out'}`}
                    aria-label="Scroll to top"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M5 10l7-7m0 0l7 7m-7-7v18"/>
                    </svg>
                </button>
            )}

            {isCachedResult && (
                <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
                    <span className="inline-block w-2 h-2 bg-blue-500 rounded-full"></span>
                    Showing cached results
                </div>
            )}

            {/* Enhanced Footer */}
            <div className="flex justify-center pb-12">
                <div className="px-6 py-3 rounded-xl bg-white/50 dark:bg-gray-900/50 border border-gray-200/50 dark:border-gray-700/50 
                    backdrop-blur-sm shadow-sm hover:shadow-md transition-all duration-300 transform hover:scale-[1.02]
                    text-sm text-gray-600 dark:text-gray-400">
                    <span className="flex items-center gap-2">
                        Made with <span className="text-blue-600 dark:text-blue-400 animate-pulse">💙</span> in Philadelphia by Brandon Hightower
                    </span>
                </div>
            </div>
        </div>
    );
};

export default PropertyReportGenerator;