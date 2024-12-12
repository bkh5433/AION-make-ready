import React, {useEffect, useState} from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Loader2, Database, RefreshCw, Server, AlertTriangle, Clock, Info, X} from 'lucide-react';

// Animated progress ring component
const ProgressRing = () => (
    <svg className="w-40 h-40" viewBox="0 0 100 100">
        <motion.circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-primary/10"
            initial={{pathLength: 0}}
            animate={{pathLength: 1}}
            transition={{duration: 2, repeat: Infinity, ease: "linear"}}
        />
    </svg>
);

const FloatingParticle = ({delay = 0, style = {}}) => (
    <motion.div
        initial={{opacity: 0, scale: 0}}
        animate={{
            opacity: [0, 1, 0],
            scale: [0.5, 1.5, 0.5],
            y: [-20, -40],
        }}
        transition={{
            duration: 2,
            delay,
            repeat: Infinity,
            ease: "easeInOut"
        }}
        className="absolute w-2 h-2 rounded-full bg-primary/30"
        style={style}
    />
);

// Time estimation component
const TimeEstimate = ({startTime}) => {
    const [elapsedTime, setElapsedTime] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setElapsedTime(prev => prev + 1);
        }, 1000);

        return () => clearInterval(interval);
    }, []);

    return (
        <motion.div
            initial={{opacity: 0}}
            animate={{opacity: 1}}
            transition={{delay: 2}}
            className="flex items-center justify-center gap-2 text-sm text-gray-400/60"
        >
            <Clock className="h-4 w-4"/>
            <span>Time elapsed: {elapsedTime}s</span>
        </motion.div>
    );
};

// Add these sophisticated animation components at the top
const PulsingRing = () => (
    <motion.div
        className="absolute inset-0"
        initial={{opacity: 0.5, scale: 0.8}}
        animate={{
            opacity: [0.5, 0.8, 0.5],
            scale: [0.8, 1.1, 0.8],
            rotate: 360
        }}
        transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
        }}
    >
        <div className="w-full h-full rounded-full border-4 border-primary/30 blur-[2px]"/>
    </motion.div>
);

const FloatingOrb = ({delay = 0, position = {}}) => (
    <motion.div
        className="absolute w-3 h-3"
        style={position}
        initial={{opacity: 0}}
        animate={{
            opacity: [0, 1, 0],
            y: [0, -20, 0],
            scale: [1, 1.5, 1]
        }}
        transition={{
            duration: 3,
            delay,
            repeat: Infinity,
            ease: "easeInOut"
        }}
    >
        <div className="w-full h-full rounded-full bg-gradient-to-r from-primary/40 to-blue-400/40 blur-[1px]"/>
    </motion.div>
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
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md"
        >
            {/* Background effects */}
            <div className="absolute inset-0">
                {/* Enhanced gradient background with multiple layers */}
                <div
                    className="absolute inset-0 bg-gradient-to-b from-gray-50 via-gray-100 to-white dark:from-gray-950 dark:via-gray-900 dark:to-black"/>
                <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-blue-500/5"/>

                {/* Animated subtle gradient overlay */}
                <motion.div
                    className="absolute inset-0 bg-gradient-to-tr from-primary/5 via-transparent to-blue-600/5 dark:from-primary/10 dark:to-blue-600/10"
                    animate={{
                        opacity: [0.5, 0.8, 0.5]
                    }}
                    transition={{
                        duration: 8,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                />

                {/* Enhanced grid with gradient mask */}
                <div
                    className="absolute inset-0 opacity-[0.05] dark:opacity-[0.07]"
                    style={{
                        backgroundImage: `
                            linear-gradient(to right, currentColor 1px, transparent 1px), 
                            linear-gradient(to bottom, currentColor 1px, transparent 1px)
                        `,
                        backgroundSize: '40px 40px',
                        maskImage: 'radial-gradient(circle at center, black 30%, transparent 80%)'
                    }}
                />

                {/* Ambient glow effects */}
                <div className="absolute inset-0 overflow-hidden">
                    {/* Primary glow */}
                    <motion.div
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px]"
                        animate={{
                            scale: [1, 1.2, 1],
                            rotate: [0, 90, 0]
                        }}
                        transition={{
                            duration: 20,
                            repeat: Infinity,
                            ease: "easeInOut"
                        }}
                    >
                        <div
                            className="absolute inset-0 bg-gradient-to-r from-primary/10 via-blue-500/10 to-primary/10 dark:from-primary/20 dark:via-blue-500/20 dark:to-primary/20 rounded-full blur-[120px]"/>
                    </motion.div>

                    {/* Secondary glow */}
                    <motion.div
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px]"
                        animate={{
                            scale: [1.2, 1, 1.2],
                            rotate: [90, 0, 90]
                        }}
                        transition={{
                            duration: 15,
                            repeat: Infinity,
                            ease: "easeInOut"
                        }}
                    >
                        <div
                            className="absolute inset-0 bg-gradient-to-bl from-blue-600/5 via-primary/5 to-blue-600/5 dark:from-blue-600/10 dark:via-primary/10 dark:to-blue-600/10 rounded-full blur-[100px]"/>
                    </motion.div>
                </div>

                {/* Subtle vignette effect */}
                <div
                    className="absolute inset-0 bg-gradient-to-r from-black/10 via-transparent to-black/10 dark:from-black/20 dark:to-black/20"/>
                <div
                    className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/10 dark:from-black/20 dark:to-black/20"/>
            </div>

            {/* Admin bypass button */}
            {isAdmin && (
                <motion.button
                    initial={{opacity: 0, y: -20}}
                    animate={{opacity: 1, y: 0}}
                    transition={{delay: 1}}
                    onClick={onAdminBypass}
                    className="fixed top-4 right-4 z-50 px-4 py-2 rounded-lg bg-yellow-500/20 hover:bg-yellow-500/30
            text-yellow-500 border border-yellow-500/20 backdrop-blur-sm transition-colors duration-200
            flex items-center gap-2 text-sm font-medium"
                >
                    <AlertTriangle className="h-4 w-4"/>
                    Admin Bypass
                </motion.button>
            )}

            {/* Info button */}
            <motion.button
                initial={{opacity: 0, scale: 0.8}}
                animate={{opacity: 1, scale: 1}}
                transition={{delay: 1.5}}
                onClick={() => setShowInfo(prev => !prev)}
                className="fixed top-4 left-4 z-50 p-2 rounded-full 
                    bg-gray-200/20 hover:bg-gray-200/30 
                    dark:bg-gray-500/20 dark:hover:bg-gray-500/30
                    text-gray-600 dark:text-gray-400 
                    backdrop-blur-sm transition-all duration-200"
            >
                <Info className="h-5 w-5"/>
            </motion.button>

            <div className="relative flex flex-col items-center justify-center max-w-2xl mx-auto p-8 text-center">
                {/* Ambient glow effects */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px]">
                    <motion.div
                        className="absolute inset-0 bg-primary/20 rounded-full blur-[100px]"
                        animate={{scale: [1, 1.05, 1]}}
                        transition={{duration: 10, repeat: Infinity, ease: "easeInOut"}}
                    />
                    <motion.div
                        className="absolute inset-0 bg-blue-500/20 rounded-full blur-[100px] animate-pulse"
                    />
                </div>

                {/* Content container */}
                <div className="relative z-10 space-y-12">
                    {/* Animated icon section */}
                    <div className="relative w-40 h-40 mx-auto">
                        <ProgressRing/>

                        {/* Floating particles */}
                        <FloatingParticle delay={0} style={{left: '20%', top: '40%'}}/>
                        <FloatingParticle delay={0.5} style={{left: '80%', top: '30%'}}/>
                        <FloatingParticle delay={1} style={{left: '50%', top: '20%'}}/>

                        {/* Rotating rings */}
                        <motion.div
                            animate={{rotate: 360}}
                            transition={{duration: 10, repeat: Infinity, ease: "linear"}}
                            className="absolute inset-0 border-2 border-primary/20 rounded-full"
                        />
                        <motion.div
                            animate={{rotate: -360}}
                            transition={{duration: 15, repeat: Infinity, ease: "linear"}}
                            className="absolute inset-2 border-2 border-primary/15 rounded-full"
                        />

                        {/* Main icon */}
                        <motion.div
                            animate={{
                                scale: [1, 1.1, 1],
                            }}
                            transition={{
                                duration: 2,
                                repeat: Infinity,
                                ease: "easeInOut"
                            }}
                            className="absolute inset-0 flex items-center justify-center"
                        >
                            <div className="relative">
                                <Database className="h-16 w-16 text-primary"/>
                                <motion.div
                                    animate={{rotate: -360}}
                                    transition={{duration: 3, repeat: Infinity, ease: "linear"}}
                                    className="absolute inset-0"
                                >
                                    <RefreshCw className="h-16 w-16 text-primary/50"/>
                                </motion.div>
                            </div>
                        </motion.div>
                    </div>

                    {/* Text content */}
                    <div className="space-y-6">
                        <motion.h2
                            initial={{opacity: 0, y: 20}}
                            animate={{opacity: 1, y: 0}}
                            transition={{delay: 0.2}}
                            className="text-5xl font-bold tracking-tight text-center"
                        >
                            <span className="bg-gradient-to-r from-primary via-blue-400 to-primary bg-clip-text text-transparent
                                [text-shadow:_0_4px_20px_rgb(0_0_0_/_20%)] dark:[text-shadow:_0_4px_20px_rgb(0_0_0_/_40%)]">
                                Database Update in Progress
                            </span>
                        </motion.h2>

                        <motion.p
                            initial={{opacity: 0, y: 20}}
                            animate={{opacity: 1, y: 0}}
                            transition={{delay: 0.4}}
                            className="text-xl text-gray-600/90 dark:text-gray-300/90 max-w-md mx-auto text-center leading-relaxed"
                        >
                            We're currently updating our database to bring you the latest property metrics.
                            Vista will be back shortly{dots}
                        </motion.p>

                        <motion.div
                            initial={{opacity: 0, y: 20}}
                            animate={{opacity: 1, y: 0}}
                            transition={{delay: 0.6}}
                            className="flex items-center justify-center gap-2 text-sm text-gray-400/80"
                        >
                            <Server className="h-4 w-4"/>
                            Go grab a cup of coffee... this might take a few minutes
                        </motion.div>

                        {/* <TimeEstimate startTime={startTime.current} /> */}

                        <AnimatePresence>
                            {showTip && (
                                <motion.div
                                    initial={{opacity: 0, y: 20}}
                                    animate={{opacity: 1, y: 0}}
                                    exit={{opacity: 0, y: -20}}
                                    className="text-sm text-gray-400/60 italic"
                                >
                                    This page will automatically refresh once the update is complete
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Info modal */}
            <AnimatePresence>
                {showInfo && (
                    <motion.div
                        initial={{opacity: 0, scale: 0.95}}
                        animate={{opacity: 1, scale: 1}}
                        exit={{opacity: 0, scale: 0.95}}
                        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
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
                                    Updates typically take around 30-60 minutes
                                </p>
                                {/* <p className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  
                </p> */}
                                {/* <p className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary" />
                  No data loss will occur
                </p> */}
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

export default MaintenancePage; 