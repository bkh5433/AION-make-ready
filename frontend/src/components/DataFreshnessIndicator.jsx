import React from 'react';
import {AlertTriangle, CheckCircle, RefreshCw, AlertCircle, Info} from 'lucide-react';

const DataFreshnessIndicator = ({
                                    isDataUpToDate,
                                    properties,
                                    periodStartDate,
                                    periodEndDate,
                                    onRefresh,
                                    isRefreshing,
                                    isAdmin = false
                                }) => {
    const formatExactDate = (date) => {
        if (!date) return null;
        const utcDate = new Date(date);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            timeZone: 'UTC'
        }).format(utcDate);
    };

    // Simplified status based only on data freshness
    const status = isDataUpToDate ? 'success' : 'error';

    // Get appropriate messaging based on status
    const getMessage = () => {
        if (!isDataUpToDate) return {
            title: 'Current Data is Out of Date',
            description: 'Property data needs to be refreshed to ensure accuracy. Some information may not reflect recent changes.'
        };

        return {
            title: 'Current Data is Up to Date',
            description: 'All property data is current and validated through yesterday. Reports will reflect the most recent information.'
        };
    };

    const message = getMessage();

    const getStatusStyles = () => {
        const styles = {
            success: {
                bg: 'before:bg-gradient-to-r before:from-green-50/90 before:to-emerald-50/90 dark:before:from-green-900/30 dark:before:to-emerald-900/20',
                border: 'after:border-b-green-200/80 dark:after:border-b-green-700/50',
                text: 'text-green-900 dark:text-green-100',
                description: 'text-green-700 dark:text-green-300'
            },
            error: {
                bg: 'before:bg-gradient-to-r before:from-red-50/90 before:to-rose-50/90 dark:before:from-red-900/30 dark:before:to-rose-900/20',
                border: 'after:border-b-red-200/80 dark:after:border-b-red-700/50',
                text: 'text-red-900 dark:text-red-100',
                description: 'text-red-700 dark:text-red-300'
            }
        };
        return styles[status];
    };

    const styles = getStatusStyles();

    const StatusIcon = () => {
        const iconProps = "w-8 h-8";
        switch (status) {
            case 'success':
                return <CheckCircle className={`${iconProps} text-green-600 dark:text-green-400`}/>;
            case 'error':
                return <AlertCircle className={`${iconProps} text-red-600 dark:text-red-400`}/>;
            default:
                return null;
        }
    };

    return (
        <div className={`
            relative flex items-start gap-6 px-8 py-7 transition-all duration-500
            -mx-8 overflow-hidden min-h-[120px]
            before:absolute before:inset-0 before:z-0
            before:backdrop-blur-md before:backdrop-saturate-150
            animate-in fade-in-0 duration-1000
            ${styles.bg}
            after:absolute after:inset-0 after:z-[1]
            after:border-b-2 after:border-b-white/20 dark:after:border-b-white/5
            ${styles.border}
            after:shadow-[0_4px_24px_-4px_rgba(0,0,0,0.1)] dark:after:shadow-[0_4px_24px_-4px_rgba(0,0,0,0.3)]
            after:animate-in after:fade-in-0 after:duration-[1200ms] after:ease-in-out
        `}>
            <div className="relative z-10 flex-shrink-0 transition-all duration-300 hover:scale-110 hover:rotate-3
                animate-in fade-in-0 zoom-in-75 duration-1000 delay-[400ms] pt-1">
                <div className="relative">
                    <div className="absolute inset-0 animate-pulse-slow blur-sm opacity-50">
                        <StatusIcon/>
                    </div>
                    <StatusIcon/>
                </div>
            </div>
            <div className="relative z-10 flex-grow animate-in slide-in-from-bottom-2 duration-1000 delay-[200ms]">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <h3 className={`font-semibold text-lg tracking-tight animate-in fade-in-0 duration-1000 delay-[600ms] ${styles.text}`}>
                            {message.title}
                        </h3>
                        <div className="flex items-center gap-2">
                            <span className="px-3.5 py-1 text-xs font-medium rounded-full 
                                bg-white/60 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300
                                border border-white/80 dark:border-gray-700/80 
                                shadow-[0_2px_8px_-2px_rgba(0,0,0,0.1)] dark:shadow-[0_2px_8px_-2px_rgba(0,0,0,0.3)]
                                backdrop-blur-sm
                                animate-in fade-in-0 duration-1000 delay-[800ms]">
                                {properties.length} Properties
                            </span>
                        </div>
                    </div>
                    {!isDataUpToDate && isAdmin && (
                        <button
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            className={`relative group flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium 
                                transition-all duration-300 transform hover:scale-102 active:scale-98
                                before:absolute before:inset-0 before:rounded-md before:transition-all
                                before:duration-300 before:z-0 hover:before:scale-105
                                animate-in fade-in-0 duration-1000 delay-[1000ms]
                                ${isRefreshing
                                ? 'before:bg-gray-100/80 dark:before:bg-gray-800/80 text-gray-400 cursor-not-allowed'
                                : 'before:bg-blue-100/80 dark:before:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:before:bg-blue-200/90 dark:hover:before:bg-blue-900/60'
                            }
                                before:backdrop-blur-sm before:shadow-lg`}
                        >
                            <span className="relative z-10 flex items-center gap-2">
                                {isRefreshing ? (
                                    <>
                                        <div
                                            className="animate-spin h-4 w-4 border-2 border-blue-600 dark:border-blue-400 border-t-transparent rounded-full"/>
                                        <span>Refreshing...</span>
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw
                                            className="h-4 w-4 transition-transform group-hover:rotate-180 duration-500"/>
                                        <span>Request Refresh</span>
                                    </>
                                )}
                            </span>
                        </button>
                    )}
                </div>
                <div className="mt-3 space-y-3">
                    <p className={`text-sm leading-relaxed animate-in fade-in-0 duration-1000 delay-[1200ms] ${styles.description}`}>
                        {message.description}
                    </p>
                    <div className="h-[32px] transition-all duration-500">
                        {periodStartDate && periodEndDate && (
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 dark:text-gray-400
                                animate-in fade-in-0 duration-1000 delay-[2000ms]">
                                <div className="flex items-center gap-3">
                                    <span className="font-medium animate-in fade-in-0 duration-1000 delay-[2200ms]">30-Day Period:</span>
                                    <span className="relative px-4 py-1.5 rounded-lg
                                        before:absolute before:inset-0 before:rounded-lg
                                        before:bg-black/5 dark:before:bg-white/5 
                                        before:backdrop-blur-sm
                                        animate-in fade-in-0 slide-in-from-bottom-1 duration-1000 delay-[2400ms]">
                                        <span className="relative z-10">
                                            {formatExactDate(periodStartDate)}
                                            {' - '}
                                            {formatExactDate(periodEndDate)}
                                            <span className="ml-2 text-xs text-gray-500 dark:text-gray-500
                                                animate-in fade-in-0 duration-1000 delay-[2600ms]">
                                                (Data complete through end of day)
                                            </span>
                                        </span>
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DataFreshnessIndicator; 