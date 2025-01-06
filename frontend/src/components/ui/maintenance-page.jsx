import React, {useEffect, useState} from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Loader2, Database, RefreshCw, Server, AlertTriangle, Clock, Info, X} from 'lucide-react';

// Optimized ProgressRing with simpler animation
const ProgressRing = () => (
    <svg className="w-40 h-40" viewBox="0 0 100 100">
        <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-gray-200/20 dark:text-gray-700/20"
        />
        <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className="text-primary animate-progress-ring"
            strokeLinecap="round"
            style={{
                strokeDasharray: '280, 360',
            }}
        />
    </svg>
);

// Simplified PulsingRing without blur
const PulsingRing = () => (
    <div className="absolute inset-0">
        <div className="w-full h-full rounded-full border-[3px] border-primary/20 animate-pulse"/>
    </div>
);

// Optimized FloatingOrb with reduced opacity changes
const FloatingOrb = ({delay = 0, position = {}}) => (
    <div
        className="absolute w-2 h-2 animate-float-orb"
        style={{
            ...position,
            animationDelay: `${delay}s`
        }}
    >
        <div className="w-full h-full rounded-full bg-primary/30"/>
    </div>
);

const MaintenancePage = ({onCheckStatus, isAdmin, onAdminBypass}) => {
    const [dots, setDots] = useState('');
    const [showTip, setShowTip] = useState(false);
    const [showInfo, setShowInfo] = useState(false);
    const startTime = React.useRef(new Date());

    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => prev.length >= 3 ? '' : prev + '.');
        }, 500);

        const tipTimeout = setTimeout(() => setShowTip(true), 10000);

        return () => {
            clearInterval(interval);
            clearTimeout(tipTimeout);
        };
    }, []);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-black">
            {/* Simplified background */}
            <div className="absolute inset-0">
                <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-blue-600/5"/>
                <div
                    className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.08),transparent_100%)]"/>
            </div>

            {/* Admin bypass button */}
            {isAdmin && (
                <div className="fixed top-4 right-4 z-50">
                    <button
                        onClick={onAdminBypass}
                        className="px-4 py-2 rounded-lg bg-yellow-500/10 hover:bg-yellow-500/20
                            text-yellow-600 dark:text-yellow-500 border border-yellow-500/20 transition-colors
                            flex items-center gap-2 text-sm font-medium"
                    >
                        <AlertTriangle className="h-4 w-4"/>
                        Admin Bypass
                    </button>
                </div>
            )}

            {/* Content container */}
            <div className="relative flex flex-col items-center justify-center max-w-2xl mx-auto p-8 text-center">
                {/* Icon section */}
                <div className="relative w-40 h-40 mx-auto mb-12">
                    <ProgressRing/>
                    <PulsingRing/>

                    {/* Reduced number of orbs */}
                    <FloatingOrb delay={0} position={{left: '20%', top: '30%'}}/>
                    <FloatingOrb delay={1.5} position={{right: '20%', top: '70%'}}/>

                    {/* Simplified rotating elements */}
                    <div
                        className="absolute inset-0 border border-primary/10 rounded-full animate-[spin_20s_linear_infinite]"/>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="relative">
                            <Database className="h-16 w-16 text-primary animate-pulse"/>
                            <div className="absolute inset-0 animate-[spin_8s_linear_infinite] opacity-30">
                                <RefreshCw className="h-16 w-16 text-primary"/>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Text content */}
                <div className="space-y-6">
                    <h2 className="text-4xl font-bold tracking-tight">
                        <span className="bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
                            Database Update in Progress
                        </span>
                    </h2>

                    <p className="text-xl text-gray-600 dark:text-gray-300/90 max-w-md mx-auto leading-relaxed">
                        We're currently updating our database to bring you the latest property metrics.
                        Vista will be back shortly{dots}
                    </p>

                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500 dark:text-gray-400/90">
                        <Server className="h-4 w-4"/>
                        Go grab a cup of coffee... this might take a few minutes
                    </div>

                    <AnimatePresence>
                        {showTip && (
                            <motion.div
                                initial={{opacity: 0, y: 10}}
                                animate={{opacity: 1, y: 0}}
                                exit={{opacity: 0, y: -10}}
                                transition={{duration: 0.2}}
                                className="flex flex-col items-center gap-4"
                            >
                                <div className="text-sm text-gray-500/90 dark:text-gray-400/80 italic">
                                    This page will automatically refresh once the update is complete
                                </div>

                                <button
                                    onClick={() => setShowInfo(prev => !prev)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg 
                                        bg-gray-100 hover:bg-gray-200 dark:bg-gray-800/50 dark:hover:bg-gray-800/70
                                        text-gray-600 dark:text-gray-300 transition-colors"
                                >
                                    <Info className="h-4 w-4"/>
                                    <span className="text-sm">About Database Updates</span>
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Modal */}
            <AnimatePresence>
                {showInfo && (
                    <div
                        className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/30 dark:bg-black/60"
                        onClick={() => setShowInfo(false)}
                    >
                        <motion.div
                            initial={{scale: 0.95, opacity: 0}}
                            animate={{scale: 1, opacity: 1}}
                            exit={{scale: 0.95, opacity: 0}}
                            transition={{duration: 0.2}}
                            className="bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md w-full 
                                border border-gray-200/50 dark:border-gray-800/50 
                                shadow-xl text-left space-y-4 relative"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <button
                                onClick={() => setShowInfo(false)}
                                className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                                aria-label="Close Info Modal"
                            >
                                <X className="h-6 w-6"/>
                            </button>
                            <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200">About Database
                                Updates</h3>
                            <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
                                Each day, we receive new data from RealPage and update our database accordingly. During
                                this update process, Vista temporarily limits access to ensure the consistency and
                                integrity of the data.
                            </p>
                            <div className="text-gray-600 dark:text-gray-400 text-sm space-y-2">
                                <p className="flex items-center gap-2">
                                    <Clock className="h-4 w-4 text-primary"/>
                                    Updates typically take around 30-45 minutes
                                </p>
                            </div>
                            <button
                                onClick={() => setShowInfo(false)}
                                className="mt-4 text-sm text-primary hover:text-primary/80 transition-colors"
                            >
                                Close
                            </button>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default MaintenancePage;