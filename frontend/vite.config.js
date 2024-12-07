import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    build: {
        sourcemap: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom', 'react-router-dom'],
                    ui: ['lucide-react', '@radix-ui/react-alert-dialog']
                }
            },
            external: [
                'jszip'
            ]
        }
    },
    server: {
        proxy: {
            '/api': {
                target: process.env.VITE_API_URL || 'http://localhost:5000',
                changeOrigin: true,
                secure: false
            }
        }
    }
})
