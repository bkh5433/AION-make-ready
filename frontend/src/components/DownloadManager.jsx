import React, {useState} from 'react';
import {FileDown, CheckCircle, X, Download} from 'lucide-react';
import {Card, CardContent} from './ui/card';

const DownloadManager = ({
                             files = [],
                             onDownload,
                             onClose,
                             isVisible,
                             downloadProgress = null
                         }) => {
    const [showCompleted, setShowCompleted] = useState(true);

    const pendingFiles = files.filter(f => !f.downloaded);
    const completedFiles = files.filter(f => f.downloaded);

    // Hide the manager if there are no pending files and no download in progress
    if (!isVisible || files.length === 0 || (!pendingFiles.length && !downloadProgress)) {
        return null;
    }

    const getDisplayName = (file) => {
        const filename = file.name.split('/').pop();
        return filename;
    };

    const formatTimestamp = (timestamp) => {
        return new Date(timestamp).toLocaleString();
    };

    // Helper to render progress bar
    const renderProgress = () => {
        if (!downloadProgress) return null;

        const getProgressPercent = () => {
            if (downloadProgress.type === 'progress') {
                return (downloadProgress.completed / downloadProgress.total) * 100;
            }
            return 0;
        };

        return (
            <div className="mt-2 text-sm">
                <div className="flex justify-between text-gray-600 dark:text-gray-300 mb-1">
                    <span>{downloadProgress.message}</span>
                    {downloadProgress.type === 'progress' && (
                        <span>{downloadProgress.completed}/{downloadProgress.total}</span>
                    )}
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                    <div
                        className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                        style={{width: `${getProgressPercent()}%`}}
                    />
                </div>
            </div>
        );
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 w-96 animate-in slide-in-from-right-5">
            <Card className="bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700">
                <div className="flex flex-col">
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                                <Download className="h-5 w-5 text-blue-500"/>
                                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                                    Downloads ({files.length})
                                </h3>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setShowCompleted(!showCompleted)}
                                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                                >
                                    {showCompleted ? 'Hide' : 'Show'} Completed
                                </button>
                                <button
                                    onClick={onClose}
                                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                >
                                    <X className="h-5 w-5"/>
                                </button>
                            </div>
                        </div>
                    </div>

                    <CardContent className="p-4 max-h-96 overflow-y-auto">
                        <div className="space-y-3">
                            {/* Pending Downloads */}
                            {pendingFiles.length > 0 && (
                                <div className="mb-4">
                                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Pending ({pendingFiles.length})
                                    </h4>
                                    {pendingFiles.map((file) => (
                                        <div
                                            key={file.path}
                                            className="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 mb-2"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span
                                                    className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                                                    {getDisplayName(file)}
                                                </span>
                                                <button
                                                    onClick={() => onDownload(file)}
                                                    disabled={file.downloading || downloadProgress}
                                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all ${
                                                        file.downloading || downloadProgress
                                                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                                                            : 'bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600'
                                                    }`}
                                                >
                                                    {file.downloading ? (
                                                        <>
                                                            <div
                                                                className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"/>
                                                            <span>Downloading...</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <FileDown className="h-4 w-4"/>
                                                            <span>Download</span>
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                            <div className="text-xs text-gray-500 dark:text-gray-400">
                                                Generated: {formatTimestamp(file.timestamp)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Completed Downloads */}
                            {showCompleted && completedFiles.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Completed ({completedFiles.length})
                                    </h4>
                                    {completedFiles.map((file) => (
                                        <div
                                            key={file.path}
                                            className="flex flex-col gap-2 p-3 bg-gray-50/50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600 mb-2"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span
                                                    className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                                                    {getDisplayName(file)}
                                                </span>
                                                <div
                                                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-green-700 dark:text-green-300">
                                                    <CheckCircle className="h-4 w-4"/>
                                                    <span>Downloaded</span>
                                                </div>
                                            </div>
                                            <div className="text-xs text-gray-500 dark:text-gray-400">
                                                Generated: {formatTimestamp(file.timestamp)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </CardContent>
                </div>
            </Card>
        </div>
    );
};

export default DownloadManager;