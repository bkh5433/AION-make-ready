import React from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Tooltip} from './ui/tooltip';
import {ChevronDown} from 'lucide-react';
import {isFeatureEnabled} from '../lib/features';

// Mini progress bar component with enhanced animation
const MiniProgressBar = ({value, total, colorClass, delay = 0}) => {
    const percentage = total > 0 ? (value / total) * 100 : 0;
    return (
        <div className="w-20 h-1.5 bg-gray-200/50 dark:bg-gray-700/50 rounded-full overflow-hidden backdrop-blur-sm">
            <motion.div
                initial={{width: 0, opacity: 0, scale: 0.8}}
                animate={{
                    width: `${percentage}%`,
                    opacity: 1,
                    scale: 1
                }}
                transition={{
                    duration: 0.8,
                    delay: delay,
                    ease: [0.34, 1.56, 0.64, 1] // Custom spring effect
                }}
                className={`h-full rounded-full shadow-sm ${colorClass}`}
            />
        </div>
    );
};

// Helper function for work order type styling with enhanced colors
const getWorkOrderTypeStyle = (count, total) => {
    const percentage = total > 0 ? (count / total) * 100 : 0;
    if (percentage >= 30) return {
        text: 'text-red-600 dark:text-red-400',
        bar: 'bg-gradient-to-r from-red-500 to-red-400',
        bg: 'bg-red-50 dark:bg-red-500/10'
    };
    if (percentage >= 15) return {
        text: 'text-yellow-600 dark:text-yellow-400',
        bar: 'bg-gradient-to-r from-yellow-500 to-amber-400',
        bg: 'bg-yellow-50 dark:bg-yellow-500/10'
    };
    return {
        text: 'text-blue-600 dark:text-blue-400',
        bar: 'bg-gradient-to-r from-blue-500 to-blue-400',
        bg: 'bg-blue-50 dark:bg-blue-500/10'
    };
};

const WorkOrderTypeBreakdown = ({
                                    isExpanded,
                                    onToggle,
                                    workOrderTypes,
                                    propertyName,
                                    totalWorkOrders,
                                    workOrdersPerUnit,
                                    actual_open_work_orders,
                                    completed_work_orders,
                                    cancelled_work_orders
                                }) => {
    if (!isFeatureEnabled('WORK_ORDER_TYPES')) return null;
    if (!workOrderTypes || workOrderTypes.length === 0) return null;

    // Map of category types to their icons
    const categoryIcons = {
        'Plumbing and bath': '🔧',
        'Electrical and lighting': '⚡',
        'Heating and cooling': '❄️',
        'Appliance': '🏠',
        'General': '🔨',
        'Doors and locks': '🔑',
        'Safety equipment': '🚨',
        'Preventative maintenance': '🔄',
        'Common Area': '🏢',
        'Inspection and make ready': '📋',
        'Flooring': '🔲',
        'Grounds and landscaping': '🌳',
        'Building exterior': '🏗️',
        'HCODE': '🏗️'
    };

    // Get default icon for unknown categories
    const getIcon = (category) => categoryIcons[category] || '📝';

    // Sort work order types by count
    const sortedTypes = [...workOrderTypes].sort((a, b) => b.count - a.count);

    return (
        <div className="inline-flex flex-col items-start">
            <Tooltip content={isExpanded ? "Hide breakdown" : "Show type breakdown"}>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggle();
                    }}
                    className={`ml-2 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 
                        transition-all duration-200 ${isExpanded ? 'bg-gray-100 dark:bg-gray-700' : ''}`}
                >
                    <ChevronDown
                        className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-300
                            ${isExpanded ? 'transform rotate-180' : ''}`}
                    />
                </button>
            </Tooltip>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{opacity: 0, height: 0, y: -10}}
                        animate={{opacity: 1, height: 'auto', y: 0}}
                        exit={{opacity: 0, height: 0, y: -10}}
                        transition={{duration: 0.3, ease: [0.04, 0.62, 0.23, 0.98]}}
                        className="w-full overflow-hidden"
                        style={{marginLeft: '-200px', width: '400px'}}
                    >
                        <div
                            className="mt-3 space-y-3 bg-white/50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-200/50 dark:border-gray-700/50 backdrop-blur-sm shadow-sm">
                            <div className="flex items-center justify-between">
                                <div className="text-xs font-medium text-gray-600 dark:text-gray-300">
                                    Work Order Types
                                </div>
                                <div className="text-[10px] text-gray-500 dark:text-gray-400">
                                    Last 30 Days
                                </div>
                            </div>
                            <div className="grid grid-cols-1 gap-y-2.5">
                                {sortedTypes.map(({category, count}, index) => {
                                    const style = getWorkOrderTypeStyle(count, totalWorkOrders);
                                    const percentage = ((count / totalWorkOrders) * 100).toFixed(1);
                                    // Format the label to be more concise
                                    const label = category
                                        .replace(' and ', ' & ')
                                        .replace('maintenance', 'maint.');

                                    return (
                                        <motion.div
                                            key={category}
                                            initial={{opacity: 0, y: -10}}
                                            animate={{opacity: 1, y: 0}}
                                            transition={{
                                                duration: 0.2,
                                                delay: index * 0.05
                                            }}
                                            className={`flex items-center gap-3 p-2 rounded-lg transition-colors duration-200 group
                                                hover:${style.bg}`}
                                        >
                                            <motion.div
                                                initial={{scale: 0.5, opacity: 0}}
                                                animate={{scale: 1, opacity: 1}}
                                                transition={{
                                                    duration: 0.3,
                                                    delay: index * 0.05 + 0.1,
                                                    type: "spring",
                                                    stiffness: 300
                                                }}
                                                className="w-6 h-6 flex items-center justify-center rounded-md bg-gray-100/80 dark:bg-gray-700/80"
                                            >
                                                <span className="text-sm">{getIcon(category)}</span>
                                            </motion.div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between mb-1">
                                                    <motion.span
                                                        initial={{opacity: 0, x: -5}}
                                                        animate={{opacity: 1, x: 0}}
                                                        transition={{
                                                            duration: 0.2,
                                                            delay: index * 0.05 + 0.1
                                                        }}
                                                        className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate"
                                                    >
                                                        {label}
                                                    </motion.span>
                                                    <motion.div
                                                        initial={{opacity: 0, x: 5}}
                                                        animate={{opacity: 1, x: 0}}
                                                        transition={{
                                                            duration: 0.2,
                                                            delay: index * 0.05 + 0.1
                                                        }}
                                                        className="flex items-center gap-2"
                                                    >
                                                        <span className={`text-xs font-semibold ${style.text}`}>
                                                            {count}
                                                        </span>
                                                        <span
                                                            className={`text-[10px] font-medium ${style.text} opacity-60`}>
                                                            {percentage}%
                                                        </span>
                                                    </motion.div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <MiniProgressBar
                                                        value={count}
                                                        total={totalWorkOrders}
                                                        colorClass={style.bar}
                                                        delay={index * 0.05 + 0.2}
                                                    />
                                                </div>
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default WorkOrderTypeBreakdown; 