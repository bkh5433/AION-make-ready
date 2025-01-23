import React, {useState, useEffect, useRef} from 'react';
import {createPortal} from 'react-dom';

export const Tooltip = ({content, children, wide = false}) => {
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState({top: 0, left: 0});
    const tooltipRef = useRef(null);
    const containerRef = useRef(null);
    const [portalContainer] = useState(() => {
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.top = '0';
        div.style.left = '0';
        div.style.width = '100%';
        div.style.height = '100%';
        div.style.zIndex = '9999';
        div.style.pointerEvents = 'none';
        return div;
    });

    useEffect(() => {
        document.body.appendChild(portalContainer);
        return () => {
            document.body.removeChild(portalContainer);
        };
    }, [portalContainer]);

    const handleMouseEnter = () => {
        setIsVisible(true);
    };

    const handleMouseLeave = () => {
        setIsVisible(false);
    };

    useEffect(() => {
        if (isVisible && containerRef.current && tooltipRef.current) {
            const container = containerRef.current.getBoundingClientRect();
            const tooltip = tooltipRef.current.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;

            let top = container.bottom;
            let left = container.left + (container.width / 2);

            // Check for bottom overflow
            if (container.bottom + tooltip.height > viewportHeight) {
                top = container.top - tooltip.height;
            }

            // Check for right overflow
            if (left + (tooltip.width / 2) > viewportWidth) {
                left = container.right - tooltip.width;
            }

            // Check for left overflow
            if (left - (tooltip.width / 2) < 0) {
                left = container.left;
            }

            setPosition({
                top: `${top}px`,
                left: `${left}px`,
                transform: 'translateX(-50%)'
            });
        }
    }, [isVisible]);

    return (
        <div className="relative inline-block" ref={containerRef}>
            <div
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                className="cursor-help inline-flex items-center"
            >
                {children}
            </div>
            {isVisible && createPortal(
                <div
                    ref={tooltipRef}
                    style={{
                        position: 'fixed',
                        top: position.top,
                        left: position.left,
                        transform: position.transform,
                    }}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                    className={`${wide ? 'w-64' : 'max-w-xs'} p-2 text-sm
                              animate-in fade-in duration-200`}
                >
                    <div
                        className="relative bg-gray-900 rounded-lg p-2 text-gray-100 shadow-[0_0_0_1px_rgba(0,0,0,0.1),0_4px_6px_-1px_rgba(0,0,0,0.1),0_2px_4px_-1px_rgba(0,0,0,0.06)]">
                        {content}
                    </div>
                </div>,
                portalContainer
            )}
        </div>
    );
};