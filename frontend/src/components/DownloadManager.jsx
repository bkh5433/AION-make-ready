import React from 'react';
import {FileDown, CheckCircle, X, Download, Archive} from 'lucide-react';
import {Card, CardContent} from './ui/card';

const DownloadManager = ({
                           files = [],
                           onDownload,
                           onDownloadAll,
                           onClose,
                           isVisible,
                           downloadProgress = null // New prop for tracking zip progress
                         }) => {
  if (!isVisible || files.length === 0) return null;

  const getDisplayName = (file) => {
    const filename = file.name.split('/').pop();
    return filename;
  };

  const allDownloaded = files.every(file => file.downloaded);
  const remainingDownloads = files.filter(file => !file.downloaded).length;
  const shouldZip = remainingDownloads > 3;


  // Helper to render progress bar
  const renderProgress = () => {
    if (!downloadProgress) return null;

    const getProgressPercent = () => {
      if (downloadProgress.type === 'progress') {
        return (downloadProgress.completed / downloadProgress.total) * 100;
      }
      if (downloadProgress.type === 'compressing') {
        return downloadProgress.progress || 0;
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
                <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  <X className="h-5 w-5"/>
                </button>
              </div>

              {/* Download All Button with ZIP indication */}
              {!allDownloaded && (
                  <div className="space-y-2">
                    <button
                        onClick={() => onDownloadAll(files.filter(f => !f.downloaded))}
                        disabled={remainingDownloads === 0 || downloadProgress}
                        className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md transition-colors ${
                            downloadProgress
                                ? 'bg-gray-400 cursor-not-allowed text-white'
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                    >
                      {shouldZip ? <Archive className="h-4 w-4"/> : <Download className="h-4 w-4"/>}
                      <span>
                    {shouldZip
                        ? `Download All as ZIP (${remainingDownloads} files)`
                        : `Download All (${remainingDownloads} remaining)`
                    }
                  </span>
                    </button>

                    {renderProgress()}
                  </div>
              )}
            </div>

            <CardContent className="p-4 max-h-96 overflow-y-auto">
              <div className="space-y-3">
                {files.map((file) => (
                    <div
                        key={file.path}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
                    >
                  <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                    {getDisplayName(file)}
                  </span>
                      <button
                          onClick={() => onDownload(file)}
                          disabled={file.downloaded || file.downloading || downloadProgress}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all ${
                              file.downloaded
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                  : file.downloading || downloadProgress
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
          </div>
        </Card>
      </div>
  );
};

export default DownloadManager;