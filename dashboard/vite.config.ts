import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";

// Read version from VERSION file in project root
const versionPath = path.resolve(__dirname, "../VERSION");
const version = fs.existsSync(versionPath)
    ? fs.readFileSync(versionPath, "utf-8").trim()
    : "v0.0.0";

export default defineConfig(({ command }) => ({
    // Only use /static/ base path in production build
    base: command === "build" ? "/static/" : "/",
    plugins: [react()],
    define: {
        __APP_VERSION__: JSON.stringify(version),
    },
    // Disable public directory since we're managing static assets manually
    publicDir: false,
    build: {
        outDir: "./static",
    },
    server: {
        port: 5173,
        open: true,
        hmr: {
            overlay: true,
        },
        watch: {
            usePolling: true,
        },
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
