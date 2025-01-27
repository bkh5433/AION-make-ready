import React, {useState} from 'react';
import {Tooltip} from './ui/tooltip';
import {AlertTriangle} from 'lucide-react';
import WorkOrderTypeBreakdown from './WorkOrderTypeBreakdown';
import {isFeatureEnabled} from '../lib/features';

// Internal helper components
const StatusBadge = ({value, threshold, type}) => {
    const isHigh = value >= threshold;
    const styles = type === 'pending'
        ? {
            high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border-orange-200 dark:border-orange-800',
            normal: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700'
        }
        : {
            high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800',
            normal: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-200 dark:border-green-800'
        };

    return (
        <span className={`
      text-xs inline-flex items-center px-3 py-1 rounded-full font-medium whitespace-nowrap
      border ${isHigh ? styles.high : styles.normal}
      transition-colors duration-200
    `}>
      {isHigh ? (type === 'pending' ? 'High pending' : 'High volume') : 'Normal'}
    </span>
    );
};

const PropertyRow = ({property, onSelect, isSelected, animationDelay}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const {
        PropertyName,
        PropertyKey,
        unitCount,
        metrics: {
            actual_open_work_orders,
            pending_work_orders,
            completed_work_orders,
            cancelled_work_orders,
            percentage_completed,
            average_days_to_complete,
            work_order_types
        }
    } = property;

    const workOrdersPerUnit = actual_open_work_orders / unitCount;
    const pendingPerUnit = pending_work_orders / unitCount;
    const totalWorkOrders = actual_open_work_orders || 1;

    const handleClick = () => onSelect(PropertyKey);
    const handleCheckboxClick = (e) => {
        e.stopPropagation();
        handleClick();
    };

    return (
        <tr
            onClick={handleClick}
            className={`
                group cursor-pointer
                transition-colors duration-200
                ${isSelected
                ? 'bg-blue-50/90 dark:bg-blue-900/30 hover:!bg-blue-100/90 dark:hover:!bg-blue-900/40'
                : 'hover:bg-gray-50/90 dark:hover:bg-gray-800/50'
            }
                animate-table-stagger
            `}
            style={{
                animationDelay: `${animationDelay * 2.5}ms`,
                willChange: 'transform, opacity, background-color'
            }}
            role="row"
        >
            {/* Checkbox Column */}
            <td className="px-8 py-6" onClick={e => e.stopPropagation()}>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={handleCheckboxClick}
                    className={`
                        rounded transition-all duration-200 cursor-pointer
                        ${isSelected
                        ? 'bg-blue-500/20 border-blue-400 dark:border-blue-400'
                        : 'border-gray-300 dark:border-gray-600 bg-white/80 dark:bg-gray-700/80'
                    }
                        text-blue-500 dark:text-blue-400
                        focus:ring-blue-500/50 focus:ring-offset-0
                        group-hover:border-blue-400 dark:group-hover:border-blue-300
                    `}
                    aria-label={`Select ${PropertyName}`}
                />
            </td>

            {/* Property Info Column */}
            <td className="px-8 py-6">
                <div className="flex flex-col transition-transform duration-150 ease-out group-hover:translate-x-1">
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                        {PropertyName}
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                        {average_days_to_complete > 5 && (
                            <Tooltip
                                content={`Average completion time per work order: ${average_days_to_complete.toFixed(1)} days`}>
                                <span className="px-2 py-0.5 text-xs rounded-full 
                                    bg-yellow-100/80 dark:bg-yellow-900/30 
                                    text-yellow-800 dark:text-yellow-200
                                    border border-yellow-200/50 dark:border-yellow-700/50
                                    backdrop-blur-sm">
                                    Avg {average_days_to_complete.toFixed(1)} days
                                </span>
                            </Tooltip>
                        )}
                    </div>
                </div>
            </td>

            {/* Units Column */}
            <td className="px-8 py-6">
                <div className="flex flex-col transition-transform duration-150 ease-out group-hover:translate-x-1">
                    <span className="font-medium text-gray-900 dark:text-gray-100">{unitCount}</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">Total Units</span>
                </div>
            </td>

            {/* Completion Rate Column */}
            <td className="px-8 py-6">
                <Tooltip
                    content={`${percentage_completed >= 90 ? 'Excellent' : percentage_completed >= 75 ? 'Good' : 'Needs attention'}: ${percentage_completed}% completion rate`}>
                    <div
                        className="flex items-center gap-2 transition-transform duration-150 ease-out group-hover:translate-x-1">
                        <div
                            className="w-24 bg-gray-200/80 dark:bg-gray-700/80 rounded-full h-2 overflow-hidden backdrop-blur-sm">
                            <div
                                className={`h-2 rounded-full transform origin-left transition-all duration-500
                                    ${percentage_completed >= 90
                                    ? 'bg-gradient-to-r from-emerald-600/90 via-green-500/90 to-emerald-400/90'
                                    : percentage_completed >= 75
                                        ? 'bg-gradient-to-r from-amber-500/90 via-yellow-500/90 to-amber-400/90'
                                        : 'bg-gradient-to-r from-red-600/90 via-red-500/90 to-red-400/90'
                                }`}
                                style={{
                                    width: `${percentage_completed}%`,
                                    transform: 'scaleX(0)',
                                    animation: 'progress-scale 0.6s ease-out forwards'
                                }}
                            />
                        </div>
                        <span className={`text-sm font-medium transition-colors duration-200 ${
                            percentage_completed >= 90 ? 'text-emerald-600 dark:text-emerald-400' :
                                percentage_completed >= 75 ? 'text-amber-600 dark:text-amber-400' :
                                    'text-red-600 dark:text-red-400'
                        }`}>
                            {percentage_completed.toFixed(1)}%
                        </span>
                    </div>
                </Tooltip>
                <div
                    className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mt-1 transition-transform duration-150 ease-out group-hover:translate-x-1">
                    <span>{completed_work_orders} completed</span>
                    {cancelled_work_orders > 0 && (
                        <Tooltip
                            content={`${cancelled_work_orders} work orders cancelled in the last 30 days (${((cancelled_work_orders / actual_open_work_orders) * 100).toFixed(1)}% of created work orders)`}>
                            <span className="text-red-500 dark:text-red-400">
                                • {cancelled_work_orders} cancelled
                            </span>
                        </Tooltip>
                    )}
                </div>
            </td>

            {/* Work Orders Column */}
            <td className="hidden md:table-cell px-8 py-6">
                <div
                    className="flex flex-col gap-4 transition-transform duration-150 ease-out group-hover:translate-x-1">
                    {/* Open Work Orders Section */}
                    <div className="flex flex-col">
                        <Tooltip
                            content={`Open Work Orders show all maintenance tasks created during the last 30 days for ${PropertyName} that are not canceled. These tasks are new to the reporting period and may include completed tasks.`}
                            side="left"
                            sideOffset={5}
                            wide>
                            <span
                                className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1 cursor-help">
                                Work Orders Created (Last 30 Days)
                                <span className="ml-1 text-gray-400">ⓘ</span>
                            </span>
                        </Tooltip>
                        <div className="flex flex-col">
                            <div className="flex items-center gap-2">
                                <Tooltip
                                    content={`Status Overview for ${PropertyName}:
                                        • ${actual_open_work_orders} work orders created in last 30 days
                                        • ${workOrdersPerUnit.toFixed(2)} new work orders per unit
                                        • ${completed_work_orders} completed in current period
                                        ${cancelled_work_orders > 0 ? `\n• ${cancelled_work_orders} cancelled in last 30 days (${((cancelled_work_orders / actual_open_work_orders) * 100).toFixed(1)}% of created work orders)` : ''}
                                        
                                        ${workOrdersPerUnit >= 0.5
                                        ? '\nAlert: High number of work orders relative to unit count.'
                                        : '\nStatus: Work order volume is within expected range.'
                                    }`}
                                    side="left"
                                    sideOffset={5}
                                    wide>
                                    <span className={`text-lg font-medium transition-colors duration-200 cursor-help ${
                                        workOrdersPerUnit >= 0.5 ? 'text-red-600 dark:text-red-400' :
                                        workOrdersPerUnit >= 0.25 ? 'text-yellow-600 dark:text-yellow-400' :
                                            'text-green-600 dark:text-green-400'
                                    }`}>
                                        {actual_open_work_orders}
                                    </span>
                                </Tooltip>
                                <StatusBadge
                                    value={workOrdersPerUnit}
                                    threshold={0.5}
                                    type="open"
                                />
                                <WorkOrderTypeBreakdown
                                    isExpanded={isExpanded}
                                    onToggle={() => setIsExpanded(!isExpanded)}
                                    workOrderTypes={work_order_types}
                                    propertyName={PropertyName}
                                    totalWorkOrders={totalWorkOrders}
                                    workOrdersPerUnit={workOrdersPerUnit}
                                    actual_open_work_orders={actual_open_work_orders}
                                    completed_work_orders={completed_work_orders}
                                    cancelled_work_orders={cancelled_work_orders}
                                />
                            </div>

                            <span className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                {workOrdersPerUnit.toFixed(2)} per unit
                            </span>
                        </div>
                    </div>

                    {/* Pending Work Orders Section */}
                    <div className="flex flex-col">
                        <Tooltip
                            content={`Pending Work Orders represent all unresolved maintenance tasks for ${PropertyName} at the end of the reporting period. This includes both tasks carried over from prior periods and those created during the last 30 days that have not been completed or canceled.`}
                            side="left"
                            sideOffset={5}
                            wide>
                            <span
                                className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400 mb-1 cursor-help">
                                Unresolved Work Orders
                                <span className="ml-1 text-gray-400">ⓘ</span>
                            </span>
                        </Tooltip>
                        <div className="flex items-center gap-2">
                            <Tooltip
                                content={`
                                    Unresolved Work Order Details:
                                    • ${pending_work_orders} unresolved tasks (includes tasks from prior periods)
                                    • ${completed_work_orders} completed in current period
                                    • ${cancelled_work_orders} cancelled in last 30 days
                                    • ${percentage_completed.toFixed(1)}% completion rate for current period
                                `}
                                side="left"
                                sideOffset={5}
                                wide>
                                <span className={`text-lg font-medium transition-colors duration-200 cursor-help ${
                                    pendingPerUnit >= 0.25 ? 'text-orange-600 dark:text-orange-400' :
                                        pendingPerUnit >= 0.1 ? 'text-amber-600 dark:text-amber-400' :
                                            'text-gray-600 dark:text-gray-400'
                                }`}>
                                    {pending_work_orders}
                                </span>
                            </Tooltip>
                            <StatusBadge
                                value={pendingPerUnit}
                                threshold={0.25}
                                type="pending"
                            />
                        </div>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                            {pendingPerUnit.toFixed(2)} per unit
                        </span>
                    </div>
                </div>
            </td>
        </tr>
    );
};

export default PropertyRow; 