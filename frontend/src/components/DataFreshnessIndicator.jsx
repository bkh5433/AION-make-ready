import React from 'react';
import {AlertTriangle, CheckCircle, RefreshCw} from 'lucide-react';

const DataFreshnessIndicator = ({
                                    isDataUpToDate,
                                    properties,
                                    periodStartDate,
                                    periodEndDate,
                                    onRefresh,
                                    isRefreshing,
                                    isAdmin = false,
                                    formatDate
                                }) => {
    // Format the dates exactly as they come from the API
    const formatExactDate = (date) => {
        if (!date) return null;
        // Keep the date in UTC/GMT format to match the report
        const utcDate = new Date(date);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            timeZone: 'UTC'  // Force UTC to match backend dates
        }).format(utcDate);
    };

    return (
        <div className={`
      flex items-center gap-3 p-8 transition-all duration-300 animate-scale-in
      -mx-8
      ${isDataUpToDate
            ? 'bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-700'
            : 'bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-700'
        }`}>
            <div className="flex-shrink-0">
                {isDataUpToDate ? (
                    <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400"/>
                ) : (
                    <AlertTriangle className="w-6 h-6 text-yellow-600 dark:text-yellow-400"/>
                )}
            </div>
            <div className="flex-grow">
                <div className="flex items-center justify-between">
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
                    {!isDataUpToDate && isAdmin && (
                        <button
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium 
              transition-all duration-200 transform hover:scale-105 active:scale-95
              ${isRefreshing
                                ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
                                : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-900/50'
                            }`}
                        >
                            {isRefreshing ? (
                                <>
                                    <div
                                        className="animate-spin h-4 w-4 border-2 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full"/>
                                    <span>Refreshing...</span>
                                </>
                            ) : (
                                <>
                                    <RefreshCw className="h-4 w-4"/>
                                    <span>Force Refresh</span>
                                </>
                            )}
                        </button>
                    )}
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
                                    {formatExactDate(periodStartDate)}
                                    {' - '}
                                    {formatExactDate(periodEndDate)}
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
    );
};

export default DataFreshnessIndicator; 