export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function debounce(func, wait) {
    let timeout;
    let promise;

    // Create a debounced function that returns a promise
    const debounced = function (...args) {
        // Clear any existing timeout
        if (timeout) {
            clearTimeout(timeout);
        }

        // Create and return a new promise
        promise = new Promise((resolve, reject) => {
            timeout = setTimeout(() => {
                try {
                    resolve(func.apply(this, args));
                } catch (err) {
                    reject(err);
                }
            }, wait);
        });

        return promise;
    };

    // Add cancel method to clear timeout
    debounced.cancel = function () {
        if (timeout) {
            clearTimeout(timeout);
            timeout = null;
        }
    };

    return debounced;
}