import React, {useEffect, useState} from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Loader2, Database, RefreshCw, Server, AlertTriangle, Clock, Info, X} from 'lucide-react';

// Simplified ProgressRing with CSS animation
const ProgressRing = () => (
    <svg className="w-40 h-40" viewBox="0 0 100 100">
        <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-gray-700/30"
        />
        <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-primary origin-center rotate-0 animate-[spin_3s_linear_infinite]"
            strokeLinecap="round"
            style={{
                strokeDasharray: '280, 360',
            }}
        />
    </svg>
);

// Replace the PulsingRing with a more efficient version using CSS animations
const PulsingRing = () => (
    <div className="absolute inset-0">
        <div className="w-full h-full rounded-full border-4 border-primary/30 blur-[2px] animate-pulse-ring"/>
    </div>
);

// Optimize FloatingOrb to use CSS animations where possible
const FloatingOrb = ({delay = 0, position = {}}) => (
    <div
        className="absolute w-3 h-3 animate-float-orb"
        style={{
            ...position,
            animationDelay: `${delay}s`
        }}
    >
        <div className="w-full h-full rounded-full bg-gradient-to-r from-primary/40 to-blue-400/40 blur-[1px]"/>
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

        // Show tip after 10 seconds
        const tipTimeout = setTimeout(() => setShowTip(true), 10000);

        return () => {
            clearInterval(interval);
            clearTimeout(tipTimeout);
        };
    }, []);

    return (
        <motion.div
            initial={{opacity: 0}}
            animate={{opacity: 1}}
            exit={{opacity: 0}}
            transition={{duration: 0.3, ease: "easeOut"}}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md"
        >
            {/* Background with blur */}
            <div className="absolute inset-0">
                {/* Static gradient layers */}
                <div
                    className="absolute inset-0 bg-gradient-to-b from-gray-50 via-gray-100 to-white dark:from-gray-950 dark:via-gray-900 dark:to-black"/>
                <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-blue-500/5"/>

                {/* Keep initial motion animation for the main content */}
                <motion.div
                    initial={{opacity: 0, y: 20}}
                    animate={{opacity: 1, y: 0}}
                    transition={{delay: 0.2}}
                    className="absolute inset-0 bg-gradient-to-tr from-primary/5 via-transparent to-blue-600/5 dark:from-primary/10 dark:to-blue-600/10 animate-fade-pulse"
                />

                {/* Simplified glow effects */}
                <div className="absolute inset-0 overflow-hidden">
                    <div
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] animate-slow-spin">
                        <div
                            className="absolute inset-0 bg-gradient-to-r from-primary/10 via-blue-500/10 to-primary/10 dark:from-primary/20 dark:via-blue-500/20 dark:to-primary/20 rounded-full blur-[120px]"/>
                    </div>
                </div>
            </div>

            {/* Admin bypass button */}
            {isAdmin && (
                <div className="fixed top-4 right-4 z-50 animate-fade-in">
                    <button
                        onClick={onAdminBypass}
                        className="px-4 py-2 rounded-lg bg-yellow-500/20 hover:bg-yellow-500/30
                            text-yellow-500 border border-yellow-500/20 backdrop-blur-sm transition-colors
                            flex items-center gap-2 text-sm font-medium"
                    >
                        <AlertTriangle className="h-4 w-4"/>
                        Admin Bypass
                    </button>
                </div>
            )}

            {/* Content container with initial animation */}
            <motion.div
                initial={{opacity: 0, y: 20}}
                animate={{opacity: 1, y: 0}}
                transition={{delay: 0.4}}
                className="relative flex flex-col items-center justify-center max-w-2xl mx-auto p-8 text-center"
            >
                {/* Simplified icon section */}
                <div className="relative w-40 h-40 mx-auto mb-12">
                    <ProgressRing/>

                    {/* Add PulsingRing for additional effect */}
                    <PulsingRing/>

                    {/* Add FloatingOrbs in different positions */}
                    <FloatingOrb delay={0} position={{left: '15%', top: '30%'}}/>
                    <FloatingOrb delay={1} position={{left: '85%', top: '30%'}}/>
                    <FloatingOrb delay={2} position={{left: '50%', top: '85%'}}/>

                    {/* Keep the existing rotating ring and database icon */}
                    <div
                        className="absolute inset-0 border-2 border-primary/10 rounded-full animate-[spin_30s_linear_infinite]"/>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="relative">
                            <Database className="h-16 w-16 text-primary"/>
                            <div className="absolute inset-0 animate-[spin_10s_linear_infinite] opacity-40">
                                <RefreshCw className="h-16 w-16 text-primary/50"/>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Text content */}
                <div className="space-y-6 animate-fade-in">
                    <h2 className="text-5xl font-bold tracking-tight text-center">
                        <span className="bg-gradient-to-r from-primary via-blue-400 to-primary bg-clip-text text-transparent
                            [text-shadow:_0_4px_20px_rgb(0_0_0_/_20%)] dark:[text-shadow:_0_4px_20px_rgb(0_0_0_/_40%)]">
                            Database Update in Progress
                        </span>
                    </h2>

                    <p className="text-xl text-gray-600/90 dark:text-gray-300/90 max-w-md mx-auto text-center leading-relaxed">
                        We're currently updating our database to bring you the latest property metrics.
                        Vista will be back shortly{dots}
                    </p>

                    <div className="flex items-center justify-center gap-2 text-sm text-gray-400/80">
                        <Server className="h-4 w-4"/>
                        Go grab a cup of coffee... this might take a few minutes
                    </div>

                    <AnimatePresence>
                        {showTip && (
                            <motion.div
                                initial={{opacity: 0, y: 20}}
                                animate={{opacity: 1, y: 0}}
                                exit={{opacity: 0, y: -20}}
                                className="flex flex-col items-center gap-4"
                            >
                                <div className="text-sm text-gray-400/60 italic">
                                    This page will automatically refresh once the update is complete
                                </div>

                                <button
                                    onClick={() => setShowInfo(prev => !prev)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg 
                                        bg-gray-700/50 hover:bg-gray-700/70
                                        text-gray-400 backdrop-blur-sm transition-colors"
                                >
                                    <Info className="h-4 w-4"/>
                                    <span className="text-sm">About Database Updates</span>
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>

            {/* Modal */}
            <AnimatePresence>
                {showInfo && (
                    <motion.div
                        initial={{opacity: 0}}
                        animate={{opacity: 1}}
                        exit={{opacity: 0}}
                        className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50"
                        onClick={() => setShowInfo(false)}
                    >
                        <motion.div
                            initial={{scale: 0.95, opacity: 0}}
                            animate={{scale: 1, opacity: 1}}
                            exit={{scale: 0.95, opacity: 0}}
                            className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md rounded-xl p-6 max-w-md w-full 
                                border border-gray-200/50 dark:border-gray-800/50 
                                shadow-2xl text-left space-y-4 relative"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <button
                                onClick={() => setShowInfo(false)}
                                className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 transition-colors"
                                aria-label="Close Info Modal"
                            >
                                <X className="h-6 w-6"/>
                            </button>
                            <h3 className="text-xl font-semibold text-gray-200">About Database Updates</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                Each day, we receive new data from RealPage and update our database accordingly. During
                                this update process, Vista temporarily limits access to ensure the consistency and
                                integrity of the data.
                            </p>
                            <div className="text-gray-400 text-sm space-y-2">
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
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

// Add to tailwind.config.js:
// theme: {
//   extend: {
//     keyframes: {
//       'fade-in': {
//         '0%': { opacity: '0' },
//         '100%': { opacity: '1' },
//       },
//       'float': {
//         '0%, 100%': { transform: 'translateY(0)', opacity: '0' },
//         '50%': { transform: 'translateY(-20px)', opacity: '0.3' },
//       },
//     },
//     animation: {
//       'fade-in': 'fade-in 0.3s ease-out',
//       'float': 'float 3s infinite ease-in-out',
//     },
//   },
// },

export default MaintenancePage; 