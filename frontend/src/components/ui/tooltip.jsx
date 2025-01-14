import React, {useState, useEffect, useRef} from 'react';

export const Tooltip = ({content, children, wide = false}) => {
    const [isVisible, setIsVisible] = useState(false);
    const [position, setPosition] = useState({top: 0, left: 0});
    const tooltipRef = useRef(null);
    const containerRef = useRef(null);

    const handleMouseEnter = () => {
        setIsVisible(true);
    };

    useEffect(() => {
        if (isVisible && containerRef.current && tooltipRef.current) {
            const container = containerRef.current.getBoundingClientRect();
            const tooltip = tooltipRef.current.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;

            // Check if tooltip would go off the bottom of the viewport
            const bottomOverflow = container.bottom + tooltip.height > viewportHeight;
            // Check if tooltip would go off the right of the viewport
            const rightOverflow = container.left + (tooltip.width / 2) > viewportWidth;
            // Check if tooltip would go off the left of the viewport
            const leftOverflow = container.left - (tooltip.width / 2) < 0;

            let top = '100%';
            let left = '50%';
            let transform = 'translateX(-50%)';
            let arrowClass = '-top-2 left-1/2 -translate-x-1/2 border-b-gray-900';

            if (bottomOverflow) {
                top = 'auto';
                transform = 'translateX(-50%) translateY(-100%)';
                arrowClass = '-bottom-2 left-1/2 -translate-x-1/2 border-t-gray-900 !border-b-transparent';
            }

            if (rightOverflow) {
                left = '0';
                transform = 'translateX(-10%)';
                arrowClass = `-${bottomOverflow ? 'bottom' : 'top'}-2 left-[10%] -translate-x-1/2 border-${bottomOverflow ? 't' : 'b'}-gray-900`;
            } else if (leftOverflow) {
                left = '100%';
                transform = 'translateX(-90%)';
                arrowClass = `-${bottomOverflow ? 'bottom' : 'top'}-2 right-[10%] translate-x-1/2 border-${bottomOverflow ? 't' : 'b'}-gray-900`;
            }

            setPosition({top, left, transform, arrowClass});
        }
    }, [isVisible]);

    return (
        <div className="relative inline-block" ref={containerRef}>
            <div
                onMouseEnter={handleMouseEnter}
                onMouseLeave={() => setIsVisible(false)}
                className="cursor-help inline-flex items-center"
            >
                {children}
            </div>
            {isVisible && (
                <div
                    ref={tooltipRef}
                    style={{
                        top: position.top,
                        left: position.left,
                        transform: position.transform
                    }}
                    className={`absolute z-[100] ${wide ? 'w-64' : 'max-w-xs'} p-2 text-sm 
                              text-gray-100 bg-gray-900/95 
                              backdrop-blur-md rounded-lg shadow-xl 
                              border border-gray-700
                              ${wide ? 'whitespace-pre-line' : 'whitespace-nowrap'}
                              animate-in fade-in duration-200`}
                >
                    {content}
                    <div className={`absolute border-8 border-transparent ${position.arrowClass}`}/>
                </div>
            )}
        </div>
    );
};