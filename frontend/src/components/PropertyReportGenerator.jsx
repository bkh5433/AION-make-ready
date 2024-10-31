import React, {useState, useEffect} from 'react';
import {Card, CardContent, CardHeader, CardTitle} from './ui/card';
import {Search, Download, FileDown, CheckCircle, X, Plus, AlertTriangle, Moon, Sun} from 'lucide-react';
import {Alert, AlertDescription} from './ui/alert';
import {Notification} from './ui/notification';
// import {ProgressBar} from './ui/ProgressBar';
import {api} from '../lib/api';
import DownloadManager from './DownloadManager';

const PropertyReportGenerator = () => {
    const [properties, setProperties] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedProperties, setSelectedProperties] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [notifications, setNotifications] = useState([]);
    const [isDataUpToDate, setIsDataUpToDate] = useState(null); // null, true, or false
    const [isDarkMode, setIsDarkMode] = useState(() => {
        const savedMode = localStorage.getItem('isDarkMode');
        return savedMode ? JSON.parse(savedMode) : false;
    });
    const [downloadManagerState, setDownloadManagerState] = useState({
        isVisible: false,
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
                    addNotification('error', `Error fetching properties (Attempt ${attempts})`);
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
    console.log('Properties before filtering:', properties);

    // Debug logging
    console.log('Raw properties before filtering:', properties);

    const filteredProperties = Array.isArray(properties)
        ? properties.filter(property => {
            // Debug log each property
            console.log('Processing property:', property);

            return property &&
                property.PropertyName &&
                property.PropertyName.toLowerCase().includes(searchTerm.toLowerCase());
        })
        : [];

    // Debug log filtered results
    console.log('Filtered properties:', filteredProperties);

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
                setNotifications([]); // Clear any existing notifications
                addNotification('success', `Successfully generated ${result.output.propertyCount} reports!`);
                setSelectedProperties([]);

                // Show the download manager if files are available
                if (result.output?.files?.length) {
                    showDownloadManager(result.output.files, result.output.directory);
                }
            } else {
                throw new Error(result.message || 'Failed to generate reports');
            }
        } catch (error) {
            console.error('Error generating reports:', error);
            addNotification('error', `Failed to generate reports: ${error.message || 'Unknown error occurred'}`);
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

    const toggleDarkMode = () => {
        setIsDarkMode((prevMode) => {
            const newMode = !prevMode;
            localStorage.setItem('isDarkMode', JSON.stringify(newMode));
            return newMode;
        });

        const ProgressBar = () => {
            return (
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                    <div className="bg-blue-600 h-2.5 rounded-full animate-indeterminate"></div>
                </div>
            );
        };
    };

    const showDownloadManager = (files, outputDirectory) => {
        setDownloadManagerState({
            isVisible: true,
            files: files.map(file => ({
                name: file,
                path: `${outputDirectory}/${file}`,
                downloaded: false,
                downloading: false
            }))
        });
    };

    const hideDownloadManager = () => {
        setDownloadManagerState(prev => ({
            ...prev,
            isVisible: false
        }));
    };

    const handleDownload = async (file) => {
        // Update file status to downloading
        setDownloadManagerState(prev => ({
            ...prev,
            files: prev.files.map(f =>
                f.path === file.path
                    ? {...f, downloading: true}
                    : f
            )
        }));

        try {
            await api.downloadReport(file.path);

            // Update file status to downloaded
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
            addNotification('error', `Failed to download ${file.name}`);

            // Reset downloading state on error
            setDownloadManagerState(prev => ({
                ...prev,
                files: prev.files.map(f =>
                    f.path === file.path
                        ? {...f, downloading: false}
                        : f
                )
            }));
        }
    };


    // Debug render
    console.log('Rendering with:', {
        propertiesLength: properties?.length,
        filteredLength: filteredProperties?.length,
        isLoading,
        error
    });

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
            <DownloadManager
                files={downloadManagerState.files}
                isVisible={downloadManagerState.isVisible}
                onDownload={handleDownload}
                onClose={hideDownloadManager}
            />

            <button
                onClick={toggleDarkMode}
                className="text-gray-500 hover:text-gray-700 focus:outline-none"
                aria-label="Toggle Dark Mode"
            >
                {isDarkMode ? <Sun className="w-6 h-6"/> : <Moon className="w-6 h-6"/>}
            </button>
        </div>
    );
};

export default PropertyReportGenerator;