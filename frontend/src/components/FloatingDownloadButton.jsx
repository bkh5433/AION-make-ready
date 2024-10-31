import React from 'react';
import {Download, X} from 'lucide-react';

const FloatingDownloadButton = ({
                                    filesCount,
                                    completedCount,
                                    onClick,
                                    className = ''
                                }) => {
    return (
        <button
            onClick={onClick}
            className={`fixed bottom-6 right-6 z-50 group flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 animate-in fade-in slide-in-from-right-5 ${className}`}
            title="Open Download Manager"
        >
            <Download className="h-5 w-5"/>
            <span className="text-sm font-medium">
        {completedCount}/{filesCount} Downloads
      </span>

            {/* Progress ring */}
            <svg className="absolute -inset-0.5 text-blue-600" viewBox="0 0 100 100">
                <circle
                    cx="50"
                    cy="50"
                    r="48"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={`${(completedCount / filesCount) * 301} 301`}
                    className="transform -rotate-90 origin-center transition-all duration-300"
                />
            </svg>
        </button>
    );
};

export default FloatingDownloadButton;