import React, {useEffect} from 'react';
import {CheckCircle, XCircle, Info, X} from 'lucide-react';

export const Notification = ({type = 'info', message, onClose, showClose = true, duration = 5000}) => {
    useEffect(() => {
        if (duration && onClose) {
            const timer = setTimeout(() => {
                onClose();
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const icons = {
        success: <CheckCircle className="h-5 w-5 text-green-400"/>,
        error: <XCircle className="h-5 w-5 text-red-400"/>,
        info: <Info className="h-5 w-5 text-blue-400"/>
    };

    const backgrounds = {
        success: 'bg-green-50 border-green-100',
        error: 'bg-red-50 border-red-100',
        info: 'bg-blue-50 border-blue-100'
    };

    return (
        <div className={`flex items-center gap-3 p-4 rounded-lg border ${backgrounds[type]} shadow-lg max-w-md`}>
            {icons[type]}
            <p className="flex-1 text-sm text-gray-600">{message}</p>
            {showClose && onClose && (
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                    <X className="h-4 w-4"/>
                </button>
            )}
        </div>
    );
};