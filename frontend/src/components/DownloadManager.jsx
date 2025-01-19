import React, {useState} from 'react';
import {FileDown, CheckCircle, X, Download, Loader2} from 'lucide-react';
import {Card, CardContent} from './ui/card';
import {motion, AnimatePresence} from 'framer-motion';
import {createPortal} from 'react-dom';

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

    const FileCard = ({file, isPending = true}) => {
        return (
            <div
                className={`
                    group relative overflow-hidden
                    rounded-lg border transition-colors duration-200
                    ${isPending
                    ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500'
                    : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200/50 dark:border-gray-700/50'
                }
                `}
            >
                <div className="p-4">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                                <div className={`
                                    flex items-center justify-center w-10 h-10 rounded-lg
                                    ${isPending ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-green-100 dark:bg-green-900/30'}
                                `}>
                                    {file.downloading ? (
                                        <Loader2 className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400"/>
                                    ) : isPending ? (
                                        <FileDown className="h-5 w-5 text-blue-600 dark:text-blue-400"/>
                                    ) : (
                                        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400"/>
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                        {getDisplayName(file)}
                                    </h4>
                                    <div className="flex items-center gap-2 mt-1">
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            Generated: {formatTimestamp(file.timestamp)}
                                        </p>
                                        {file.status && (
                                            <>
                                                <span className="text-gray-300 dark:text-gray-600">•</span>
                                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                                    {file.status}
                                                </p>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {isPending && (
                            <motion.button
                                whileHover={{scale: 1.02}}
                                whileTap={{scale: 0.98}}
                                onClick={() => onDownload(file)}
                                disabled={file.downloading || downloadProgress}
                                className={`
                                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                                    transition-colors duration-200 shadow-sm
                                    ${file.downloading || downloadProgress
                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500'
                                }
                                `}
                            >
                                {file.downloading ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin"/>
                                        <span>Downloading...</span>
                                    </>
                                ) : (
                                    <>
                                        <Download className="h-4 w-4"/>
                                        <span>Download</span>
                                    </>
                                )}
                            </motion.button>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    const content = (
        <div className="fixed bottom-6 right-6 z-50" style={{width: '450px'}}>
            <motion.div
                initial={{opacity: 0, scale: 0.95}}
                animate={{opacity: 1, scale: 1}}
                exit={{opacity: 0, scale: 0.95}}
                transition={{duration: 0.2}}
            >
                <Card className="bg-white dark:bg-gray-800 shadow-xl border border-gray-200 dark:border-gray-700">
                    <div className="flex flex-col">
                        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div
                                        className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                                        <Download className="h-4 w-4 text-blue-600 dark:text-blue-400"/>
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                                            Downloads
                                        </h3>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            {files.length} file{files.length !== 1 ? 's' : ''}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setShowCompleted(!showCompleted)}
                                        className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 
                                            hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                                    >
                                        {showCompleted ? 'Hide' : 'Show'} Completed
                                    </button>
                                    <button
                                        onClick={onClose}
                                        className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                                            transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                                    >
                                        <X className="h-5 w-5"/>
                                    </button>
                                </div>
                            </div>
                            {downloadProgress && (
                                <div className="mt-2">
                                    <div className="flex justify-between text-sm text-gray-600 dark:text-gray-300 mb-1">
                                        <span className="flex items-center gap-2">
                                            <Loader2 className="h-4 w-4 animate-spin"/>
                                            {downloadProgress.message}
                                        </span>
                                        {downloadProgress.type === 'progress' && (
                                            <span className="font-medium">
                                                {downloadProgress.completed}/{downloadProgress.total}
                                            </span>
                                        )}
                                    </div>
                                    <div
                                        className="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                                        <motion.div
                                            className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
                                            initial={{width: 0}}
                                            animate={{width: `${(downloadProgress.completed / downloadProgress.total) * 100}%`}}
                                            transition={{duration: 0.2}}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>

                        <CardContent className="p-4 max-h-[calc(100vh-300px)] overflow-y-auto">
                            <div className="space-y-4">
                                {/* Pending Downloads */}
                                {pendingFiles.length > 0 && (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                Pending
                                            </h4>
                                            <span className="px-2.5 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 
                                                bg-blue-100 dark:bg-blue-900/30 rounded-full">
                                                {pendingFiles.length}
                                            </span>
                                        </div>
                                        <div className="space-y-3">
                                            {pendingFiles.map((file) => (
                                                <FileCard key={file.path} file={file} isPending={true}/>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Completed Downloads */}
                                {showCompleted && completedFiles.length > 0 && (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                Completed
                                            </h4>
                                            <span className="px-2.5 py-0.5 text-xs font-medium text-green-600 dark:text-green-400 
                                                bg-green-100 dark:bg-green-900/30 rounded-full">
                                                {completedFiles.length}
                                            </span>
                                        </div>
                                        <div className="space-y-3">
                                            {completedFiles.map((file) => (
                                                <FileCard key={file.path} file={file} isPending={false}/>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </div>
                </Card>
            </motion.div>
        </div>
    );

    return createPortal(content, document.body);
};

export default DownloadManager;