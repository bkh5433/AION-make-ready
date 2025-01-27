import React from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Tooltip} from './ui/tooltip';
import {ChevronDown} from 'lucide-react';
import {isFeatureEnabled} from '../lib/features';

// Mini progress bar component
const MiniProgressBar = ({value, total, colorClass, delay = 0}) => {
    const percentage = total > 0 ? (value / total) * 100 : 0;
    return (
        <div className="w-16 h-1.5 bg-gray-200/80 dark:bg-gray-700/80 rounded-full overflow-hidden">
            <motion.div
                initial={{width: 0, opacity: 0}}
                animate={{
                    width: `${percentage}%`,
                    opacity: 1
                }}
                transition={{
                    duration: 0.6,
                    delay: delay,
                    ease: [0.32, 0.72, 0, 1] // Custom easing for springy effect
                }}
                className={`h-full rounded-full ${colorClass}`}
            />
        </div>
    );
};

// Helper function for work order type styling
const getWorkOrderTypeStyle = (count, total) => {
    const percentage = total > 0 ? (count / total) * 100 : 0;
    if (percentage >= 30) return {
        text: 'text-red-600 dark:text-red-400',
        bar: 'bg-red-500/90'
    };
    if (percentage >= 15) return {
        text: 'text-yellow-600 dark:text-yellow-400',
        bar: 'bg-yellow-500/90'
    };
    return {
        text: 'text-gray-600 dark:text-gray-400',
        bar: 'bg-blue-500/90'
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

    const {
        plumbing = 12,
        electrical = 8,
        hvac = 15,
        appliance = 5,
        general = 7,
        other = 3
    } = workOrderTypes || {};

    return (
        <div className="inline-flex flex-col items-start">
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onToggle();
                }}
                className={`ml-2 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 
                    transition-all duration-200 ${isExpanded ? 'bg-gray-100 dark:bg-gray-700' : ''}`}
            >
                <ChevronDown
                    className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-200
                        ${isExpanded ? 'transform rotate-180' : ''}`}
                />
            </button>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{opacity: 0, height: 0, y: -10}}
                        animate={{opacity: 1, height: 'auto', y: 0}}
                        exit={{opacity: 0, height: 0, y: -10}}
                        transition={{duration: 0.2}}
                        className="w-full overflow-hidden"
                        style={{marginLeft: '-200px', width: '400px'}}
                    >
                        <div
                            className="mt-3 space-y-2 bg-gray-50/50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200/50 dark:border-gray-700/50">
                            <div className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-2">Type Breakdown
                            </div>
                            <div className="grid grid-cols-1 gap-y-2">
                                {[
                                    {label: 'Plumbing', count: plumbing, icon: '🔧'},
                                    {label: 'Electrical', count: electrical, icon: '⚡'},
                                    {label: 'HVAC', count: hvac, icon: '❄️'},
                                    {label: 'Appliance', count: appliance, icon: '🏠'},
                                    {label: 'General', count: general, icon: '🔨'},
                                    {label: 'Other', count: other, icon: '📋'}
                                ].map(({label, count, icon}, index) => {
                                    const style = getWorkOrderTypeStyle(count, totalWorkOrders);
                                    const percentage = ((count / totalWorkOrders) * 100).toFixed(1);

                                    return (
                                        <motion.div
                                            key={label}
                                            initial={{opacity: 0, y: -10}}
                                            animate={{opacity: 1, y: 0}}
                                            transition={{
                                                duration: 0.2,
                                                delay: index * 0.05
                                            }}
                                            className="flex items-center gap-2 group"
                                        >
                                            <motion.span
                                                initial={{scale: 0.5, opacity: 0}}
                                                animate={{scale: 1, opacity: 1}}
                                                transition={{
                                                    duration: 0.2,
                                                    delay: index * 0.05 + 0.1
                                                }}
                                                className="w-5 text-xs"
                                            >
                                                {icon}
                                            </motion.span>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between mb-1">
                                                    <motion.span
                                                        initial={{opacity: 0, x: -5}}
                                                        animate={{opacity: 1, x: 0}}
                                                        transition={{
                                                            duration: 0.2,
                                                            delay: index * 0.05 + 0.1
                                                        }}
                                                        className="text-xs text-gray-600 dark:text-gray-400 truncate"
                                                    >
                                                        {label}
                                                    </motion.span>
                                                    <motion.span
                                                        initial={{opacity: 0, x: 5}}
                                                        animate={{opacity: 1, x: 0}}
                                                        transition={{
                                                            duration: 0.2,
                                                            delay: index * 0.05 + 0.1
                                                        }}
                                                        className={`text-xs font-medium ${style.text} ml-2`}
                                                    >
                                                        {count}
                                                    </motion.span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <MiniProgressBar
                                                        value={count}
                                                        total={totalWorkOrders}
                                                        colorClass={style.bar}
                                                        delay={index * 0.05 + 0.2}
                                                    />
                                                    <motion.span
                                                        initial={{opacity: 0}}
                                                        animate={{opacity: 1}}
                                                        transition={{
                                                            duration: 0.2,
                                                            delay: index * 0.05 + 0.3
                                                        }}
                                                        className={`text-[10px] font-medium ${style.text} opacity-0 group-hover:opacity-100 transition-opacity duration-200`}
                                                    >
                                                        {percentage}%
                                                    </motion.span>
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