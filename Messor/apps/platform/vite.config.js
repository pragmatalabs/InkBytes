import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import react from '@vitejs/plugin-react';

const vitePort = Number(process.env.VITE_PORT || 5173);
const viteClientPort = Number(process.env.VITE_CLIENT_PORT || vitePort);
const viteHmrHost = process.env.VITE_HMR_HOST || 'localhost';
const viteDevServerUrl = process.env.VITE_DEV_SERVER_URL || `http://${viteHmrHost}:${viteClientPort}`;
const appOrigin = process.env.VITE_APP_ORIGIN || 'http://localhost:18080';

export default defineConfig({
    server: {
        host: '0.0.0.0',
        port: vitePort,
        strictPort: true,
        origin: viteDevServerUrl,
        cors: {
            origin: [appOrigin, 'http://127.0.0.1:18080'],
        },
        hmr: {
            host: viteHmrHost,
            port: vitePort,
            clientPort: viteClientPort,
            protocol: 'ws',
        },
    },
    plugins: [
        laravel({
            input: 'resources/js/app.jsx',
            refresh: true,
        }),
        react(),
    ],
});
