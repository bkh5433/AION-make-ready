import React from 'react';
import {Download} from 'lucide-react';

const FloatingDownloadButton = ({
                                    filesCount,
                                    completedCount,
                                    onClick,
                                    className = ''
                                }) => {
    return (
        <button
            onClick={onClick}
            className={`fixed bottom-6 right-6 z-50 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 ${className}`}
            title="Open Download Manager"
        >
            <div className="flex items-center gap-2">
                <Download className="h-5 w-5"/>
                <span className="text-sm font-medium whitespace-nowrap">
                    {completedCount}/{filesCount} Downloads
                </span>
            </div>
        </button>
    );
};

export default FloatingDownloadButton;