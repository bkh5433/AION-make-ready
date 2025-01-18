import React from 'react';
import {Download} from 'lucide-react';
import {motion} from 'framer-motion';

const FloatingDownloadButton = ({
                                    filesCount,
                                    completedCount,
                                    onClick,
                                    className = ''
                                }) => {
    return (
        <motion.button
            initial={{opacity: 0, scale: 0.95, y: 20}}
            animate={{opacity: 1, scale: 1, y: 0}}
            exit={{opacity: 0, scale: 0.95, y: 20}}
            transition={{duration: 0.2}}
            whileHover={{scale: 1.02}}
            whileTap={{scale: 0.98}}
            onClick={onClick}
            className={`
                group flex items-center gap-3 px-4 py-3 
                bg-white dark:bg-gray-800 
                shadow-lg hover:shadow-xl
                border border-gray-200 dark:border-gray-700
                rounded-2xl
                transition-all duration-200
                ${className}
            `}
            title="Open Download Manager"
        >
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <Download className="h-4 w-4 text-blue-600 dark:text-blue-400"/>
            </div>
            <div className="flex flex-col items-start">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Downloads
                    </span>
                    <span className="px-2 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 
                        bg-blue-100 dark:bg-blue-900/30 rounded-full">
                        {completedCount}/{filesCount}
                    </span>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                    {filesCount - completedCount} pending
                </span>
            </div>
        </motion.button>
    );
};

export default FloatingDownloadButton;