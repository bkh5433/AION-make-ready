import React from 'react';
import {Download} from 'lucide-react';

const FloatingDownloadButton = ({
                                    filesCount,
                                    completedCount,
                                    onClick,
                                    className = ''
                                }) => {
    // Calculate progress percentage
    const progress = (completedCount / filesCount) * 100;

    return (
        <button
            onClick={onClick}
            className={`fixed bottom-6 right-6 z-50 relative inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 ${className}`}
            title="Open Download Manager"
        >
            {/* Background circle for progress ring */}
            <svg
                className="absolute inset-0 w-full h-full -z-10"
                viewBox="0 0 100 100"
            >
                {/* Background circle */}
                <circle
                    cx="50"
                    cy="50"
                    r="48"
                    fill="none"
                    stroke="rgba(255,255,255,0.2)"
                    strokeWidth="2"
                />
                {/* Progress circle */}
                <circle
                    cx="50"
                    cy="50"
                    r="48"
                    fill="none"
                    stroke="rgba(255,255,255,0.8)"
                    strokeWidth="2"
                    strokeDasharray="301"
                    strokeDashoffset={301 - ((progress) / 100 * 301)}
                    className="transform -rotate-90 origin-center transition-all duration-300"
                />
            </svg>

            {/* Content */}
            <div className="flex items-center gap-2 z-10">
                <Download className="h-5 w-5"/>
                <span className="text-sm font-medium whitespace-nowrap">
                    {completedCount}/{filesCount} Downloads
                </span>
            </div>
        </button>
    );
};

export default FloatingDownloadButton;