import React, {useState} from 'react';

export const Tooltip = ({content, children}) => {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div className="relative inline-block">
            <div
                onMouseEnter={() => setIsVisible(true)}
                onMouseLeave={() => setIsVisible(false)}
                className="cursor-help"
            >
                {children}
            </div>
            {isVisible && (
                <div
                    className="absolute z-50 w-64 p-2 mt-2 text-sm text-gray-100 bg-gray-800 rounded-lg shadow-lg whitespace-pre-line">
                    {content}
                </div>
            )}
        </div>
    );
};