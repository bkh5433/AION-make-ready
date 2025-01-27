// Feature flags configuration
export const FEATURES = {
    WORK_ORDER_TYPES: false, // Set to true to enable work order type breakdown
};

// Helper function to check if a feature is enabled
export const isFeatureEnabled = (featureKey) => {
    // Check if the feature exists and is enabled
    if (!(featureKey in FEATURES)) {
        console.warn(`Feature "${featureKey}" not found in feature flags configuration`);
        return false;
    }

    // Check for override in localStorage (useful for testing)
    const localOverride = localStorage.getItem(`feature_${featureKey}`);
    if (localOverride !== null) {
        return localOverride === 'true';
    }

    return FEATURES[featureKey];
};

// Helper function to toggle a feature (useful for testing)
export const toggleFeature = (featureKey) => {
    if (!(featureKey in FEATURES)) {
        console.warn(`Feature "${featureKey}" not found in feature flags configuration`);
        return;
    }

    const currentValue = isFeatureEnabled(featureKey);
    localStorage.setItem(`feature_${featureKey}`, (!currentValue).toString());
}; 