import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
    // Only use /static/ base path in production build
    base: command === "build" ? "/static/" : "/",
    plugins: [react()],
    // Disable public directory since we're managing static assets manually
    publicDir: false,
    build: {
        outDir: "./static",
    },
    server: {
        port: 5173,
        open: true,
        proxy: {
            // Proxy GraphQL requests to backend
            "/graphql": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
            // Proxy artifact API requests to backend
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
}));
