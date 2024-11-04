import JSZip from 'jszip';

export class ZipDownloader {
    constructor(options = {}) {
        this.onProgress = options.onProgress || (() => {
        });
        this.onFileComplete = options.onFileComplete || (() => {
        });
        this.onError = options.onError || (() => {
        });
        this.onSuccess = options.onSuccess || (() => {
        });
        this.api = options.api;
    }

    /**
     * Create and download a zip file containing multiple files
     * @param {Array} files - Array of file objects with name and path properties
     * @param {string} zipName - Name for the zip file
     */
    async downloadAsZip(files, zipName) {
        const zip = new JSZip();
        const downloadPromises = [];
        let completedFiles = 0;

        try {
            // Start progress
            this.onProgress({
                type: 'start',
                total: files.length,
                message: `Preparing ${files.length} files for download...`
            });

            // Download all files and add them to the zip
            for (const file of files) {
                const downloadPromise = this.api.downloadReport(file.path)
                    .then(async (blob) => {
                        // Add file to zip
                        zip.file(file.name, blob);

                        completedFiles++;

                        // Report individual file completion
                        this.onFileComplete({
                            file,
                            completedFiles,
                            totalFiles: files.length
                        });

                        // Report overall progress
                        this.onProgress({
                            type: 'progress',
                            completed: completedFiles,
                            total: files.length,
                            message: `Downloaded ${completedFiles} of ${files.length} files...`
                        });
                    })
                    .catch(error => {
                        this.onError({
                            file,
                            error: error.message || 'Download failed'
                        });
                        throw error; // Re-throw to be caught by Promise.all
                    });

                downloadPromises.push(downloadPromise);
            }

            // Wait for all downloads to complete
            await Promise.all(downloadPromises);

            // Report zip creation start
            this.onProgress({
                type: 'compressing',
                message: 'Creating ZIP file...'
            });

            // Generate zip file
            const zipContent = await zip.generateAsync({
                type: 'blob',
                compression: 'DEFLATE',
                compressionOptions: {level: 6},
                onUpdate: (metadata) => {
                    this.onProgress({
                        type: 'compressing',
                        progress: metadata.percent,
                        message: 'Creating ZIP file...'
                    });
                }
            });

            // Create and trigger download
            const url = URL.createObjectURL(zipContent);
            const a = document.createElement('a');
            a.href = url;
            a.download = zipName;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Report success
            this.onSuccess({
                zipName,
                fileCount: files.length,
                size: zipContent.size
            });

        } catch (error) {
            this.onError({
                error: error.message || 'Failed to create ZIP file'
            });
            throw error;
        }
    }
}

/**
 * Create a timestamped name for the zip file
 * @param {string} prefix - Prefix for the zip file name
 * @returns {string} Formatted zip file name
 */
export const createTimestampedZipName = (prefix = 'property_reports') => {
    const timestamp = new Date().toISOString()
        .replace(/[^0-9]/g, '')
        .slice(0, 14);
    return `${prefix}_${timestamp}.zip`;
};

/**
 * Format a file size in bytes to a human-readable string
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string
 */
export const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};