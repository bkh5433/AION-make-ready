import React, {useState} from 'react';

export const Tooltip = ({content, children}) => {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div className="relative inline-block">
            <div
                onMouseEnter={() => setIsVisible(true)}
                onMouseLeave={() => setIsVisible(false)}
                className="inline-block"
            >
                {children}
            </div>
            {isVisible && (
                <div
                    className="absolute z-50 px-2 py-1 text-sm text-white bg-gray-900 dark:bg-gray-800 rounded-md shadow-lg -top-full left-1/2 transform -translate-x-1/2 -translate-y-2 whitespace-nowrap">
                    {content}
                    <div
                        className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 dark:bg-gray-800 rotate-45"/>
                </div>
            )}
        </div>
    );
}; 