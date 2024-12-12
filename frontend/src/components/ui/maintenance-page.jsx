import React, {useEffect, useState} from 'react';
import {motion, AnimatePresence} from 'framer-motion';
import {Loader2, Database, RefreshCw, Server, AlertTriangle, Clock, Info} from 'lucide-react';

// Animated progress ring component
const ProgressRing = () => (
    <svg className="w-40 h-40 absolute" viewBox="0 0 100 100">
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
            {/* Background grid effect */}
            <div
                className="absolute inset-0 opacity-[0.15]"
                style={{
                    backgroundImage: 'linear-gradient(to right, #666 1px, transparent 1px), linear-gradient(to bottom, #666 1px, transparent 1px)',
                    backgroundSize: '40px 40px'
                }}
            />

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
                className="fixed top-4 left-4 z-50 p-2 rounded-full bg-gray-500/20 hover:bg-gray-500/30
          text-gray-400 backdrop-blur-sm transition-all duration-200
          flex items-center gap-2 hover:gap-3 group"
            >
                <Info className="h-5 w-5"/>
                <span className="text-sm opacity-0 group-hover:opacity-100 transition-all duration-200">
          What's happening?
        </span>
            </motion.button>

            <div className="relative flex flex-col items-center justify-center max-w-2xl mx-auto p-8 text-center">
                {/* Ambient glow effects */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px]">
                    <div className="absolute inset-0 bg-primary/20 rounded-full blur-[100px]"/>
                    <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-[100px] animate-pulse"/>
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
                            className="text-4xl font-bold tracking-tight"
                        >
              <span className="bg-gradient-to-r from-primary via-blue-400 to-primary bg-clip-text text-transparent">
                Database Update in Progress
              </span>
                        </motion.h2>

                        <motion.p
                            initial={{opacity: 0, y: 20}}
                            animate={{opacity: 1, y: 0}}
                            transition={{delay: 0.4}}
                            className="text-xl text-gray-300/90 max-w-md mx-auto"
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
                            This usually takes a few minutes
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
                                    Tip: Our system performs regular database updates to ensure data accuracy
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
                        <div
                            className="bg-gray-900/95 backdrop-blur-sm rounded-xl p-6 max-w-md border border-gray-800
                shadow-2xl text-left space-y-4"
                            onClick={e => e.stopPropagation()}
                        >
                            <h3 className="text-xl font-semibold text-gray-200">About Database Updates</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                Once daily, we receive new data from RealPage and update our database.
                                When Vista detects these updates, we temporarily restrict access to maintain
                                data consistency and integrity.
                            </p>
                            <div className="text-gray-400 text-sm space-y-2">
                                <p className="flex items-center gap-2">
                                    <Clock className="h-4 w-4 text-primary"/>
                                    Updates typically take around 1 hour
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
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default MaintenancePage; 