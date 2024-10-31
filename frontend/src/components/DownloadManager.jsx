import React from 'react';
import {FileDown, CheckCircle, X, Download} from 'lucide-react';
import {Card, CardContent} from './ui/card';

const DownloadManager = ({
                             files = [],
                             onDownload,
                             onClose,
                             isVisible
                         }) => {
    if (!isVisible || files.length === 0) return null;

    return (
        <div className="fixed bottom-6 right-6 z-50 w-96 animate-in slide-in-from-right-5">
            <Card className="bg-white dark:bg-gray-800 shadow-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                        <Download className="h-5 w-5 text-blue-500"/>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                            Downloads ({files.length})
                        </h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    >
                        <X className="h-5 w-5"/>
                    </button>
                </div>
                <CardContent className="p-4 max-h-96 overflow-y-auto">
                    <div className="space-y-3">
                        {files.map((file) => (
                            <div
                                key={file.path}
                                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
                            >
                <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                  {file.name}
                </span>
                                <button
                                    onClick={() => onDownload(file)}
                                    disabled={file.downloaded || file.downloading}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all ${
                                        file.downloaded
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                            : file.downloading
                                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                                                : 'bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600'
                                    }`}
                                >
                                    {file.downloaded ? (
                                        <>
                                            <CheckCircle className="h-4 w-4"/>
                                            <span>Downloaded</span>
                                        </>
                                    ) : file.downloading ? (
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
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

export default DownloadManager;