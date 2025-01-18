import React from 'react';
import {Search, Download, FileDown, CheckCircle, X} from 'lucide-react';
import {motion, AnimatePresence} from 'framer-motion';

const HelpOverlay = ({isVisible, onClose}) => {
    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{opacity: 0}}
                    animate={{opacity: 1}}
                    exit={{opacity: 0}}
                    transition={{duration: 0.2}}
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    onClick={(e) => {
                        // Close when clicking the backdrop
                        if (e.target === e.currentTarget) onClose();
                    }}
                >
                    <motion.div
                        initial={{scale: 0.95, opacity: 0, y: 20}}
                        animate={{scale: 1, opacity: 1, y: 0}}
                        exit={{scale: 0.95, opacity: 0, y: 20}}
                        transition={{duration: 0.2, delay: 0.1}}
                        className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
                        onClick={(e) => e.stopPropagation()} // Prevent clicks inside from closing
                    >
                        <div className="p-6 space-y-6">
                            <motion.div
                                initial={{opacity: 0, y: -10}}
                                animate={{opacity: 1, y: 0}}
                                transition={{delay: 0.2}}
                                className="flex justify-between items-center"
                            >
                                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Welcome to
                                    Vista!</h2>
                                <button
                                    onClick={onClose}
                                    className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                                >
                                    <X className="h-6 w-6"/>
                                </button>
                            </motion.div>

                            <div className="space-y-8">
                                {[
                                    {
                                        icon: <Search className="h-5 w-5 text-blue-500"/>,
                                        title: "Searching Properties",
                                        content: "Use the search bar to find properties by name or location. The search updates in real-time as you type."
                                    },
                                    {
                                        icon: <CheckCircle className="h-5 w-5 text-green-500"/>,
                                        title: "Selecting Properties",
                                        content: "Check the properties you want to generate detailed breakeven analysis reports for. You can select multiple properties at once."
                                    },
                                    {
                                        icon: <Download className="h-5 w-5 text-blue-500"/>,
                                        title: "Generating Reports",
                                        content: "After selecting properties you want to generate breakeven analysis reports for, click the \"Generate Reports\" button which will create an Excel workbook with a breakeven analysis for each property selected. The system will process your request and notify you when reports are ready."
                                    },
                                    {
                                        icon: <FileDown className="h-5 w-5 text-purple-500"/>,
                                        title: "Managing Downloads",
                                        content: "Once reports are ready, use the download manager to access your files. A floating download button will remain available if you close the download manager."
                                    }
                                ].map((section, index) => (
                                    <motion.section
                                        key={section.title}
                                        initial={{opacity: 0, x: -20}}
                                        animate={{opacity: 1, x: 0}}
                                        transition={{delay: 0.3 + (index * 0.1)}}
                                        className="space-y-2"
                                    >
                                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center gap-2">
                                            {section.icon}
                                            {section.title}
                                        </h3>
                                        <p className="text-gray-600 dark:text-gray-400">
                                            {section.content}
                                        </p>
                                    </motion.section>
                                ))}
                            </div>

                            <motion.button
                                initial={{opacity: 0, y: 20}}
                                animate={{opacity: 1, y: 0}}
                                transition={{delay: 0.7}}
                                onClick={onClose}
                                className="mt-6 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                                    transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]"
                            >
                                Got it. Let's go!
                            </motion.button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default HelpOverlay; 