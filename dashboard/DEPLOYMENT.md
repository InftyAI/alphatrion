# Dashboard Deployment Guide

The AlphaTrion dashboard supports multiple deployment scenarios:

## Local Development

For local development with the proxy:

```bash
npm run dev
```

The dashboard will use the Vite proxy to forward API requests to `http://localhost:8000`.

## Docker Deployment

### Build the Docker image:

```bash
docker build -t alphatrion-dashboard:latest .
```

### Run with environment variable:

```bash
docker run -p 8080:8080 \
  -e VITE_API_URL=http://localhost:8000 \
  alphatrion-dashboard:latest
```

## Kubernetes Deployment

The dashboard can be deployed separately from the backend in Kubernetes.

### Configure the backend API URL in `values.yaml`:

```yaml
dashboard:
  env:
    # For internal cluster communication
    apiUrl: "http://alphatrion-server:8000"

    # For external access through ingress
    # apiUrl: "https://api.example.com"
```

### Deploy with Helm:

```bash
helm install alphatrion ./charts/alphatrion \
  --set dashboard.env.apiUrl=http://alphatrion-server:8000
```

## How It Works

The dashboard supports three layers of configuration (in order of precedence):

1. **Runtime config** (Kubernetes): `window.ENV.VITE_API_URL` - injected by `entrypoint.sh` at container startup
2. **Build-time env** (Docker): `import.meta.env.VITE_API_URL` - set during `npm run build`
3. **Relative URL** (Local dev): Empty string - uses Vite proxy

### Runtime Configuration

In production (Docker/Kubernetes), the `entrypoint.sh` script generates a `/config.js` file with:

```javascript
window.ENV = {
  VITE_API_URL: "http://alphatrion-server:8000"
};
```

This is loaded before the main application and provides runtime configuration without rebuilding the image.

## Environment Variables

- `VITE_API_URL`: Backend API base URL (e.g., `http://alphatrion-server:8000` or `https://api.example.com`)
  - Leave empty for local development with proxy
  - Set in Docker run command or Kubernetes deployment for production

## Architecture

```
┌─────────────────────┐
│   User Browser      │
└──────────┬──────────┘
           │
           │ HTTPS
           │
┌──────────▼──────────┐
│   Ingress/LB        │
│  (optional)         │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼────┐ ┌───▼─────┐
│Dashboard│ │ Backend │
│ (nginx) │ │ (API)   │
│  :8080  │ │  :8000  │
└─────────┘ └─────────┘
```

The dashboard is a static single-page application served by nginx. It communicates with the backend API using the configured `VITE_API_URL`.

## Why nginx?

The dashboard needs a web server to:
1. **Serve static files over HTTP** - HTML, JavaScript, CSS, images
2. **Handle SPA routing** - Return `index.html` for all routes (e.g., `/experiments/123`) so React Router can handle client-side routing

nginx is the industry-standard choice for serving static content in Kubernetes environments.
