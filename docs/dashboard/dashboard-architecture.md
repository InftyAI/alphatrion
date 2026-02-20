# AlphaTrion Dashboard Architecture

## Overview

The AlphaTrion dashboard consists of two separate components:
1. **Backend Server** - GraphQL API (FastAPI + Strawberry)
2. **Frontend Dashboard** - React SPA (Vite + TypeScript)

## Why the Proxy?

The `alphatrion dashboard` command includes a **built-in proxy** for backend requests. Here's why:

### Problem Without Proxy

When you run:
- Backend on `http://localhost:8000`
- Dashboard on `http://localhost:5173`

The browser blocks requests from frontend → backend due to **CORS** (Cross-Origin Resource Sharing).

### Solution: Built-in Proxy

The dashboard command acts as a **reverse proxy**:

```
Browser → Dashboard:5173 → Backend:8000
         (single origin)   (proxied)
```

This provides:
- ✅ **No CORS issues** - Browser sees single origin
- ✅ **Simple setup** - Users only need one URL
- ✅ **No rebuild required** - Works with pre-built dashboard

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User's Browser                       │
│                  http://localhost:5173                   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           alphatrion dashboard (port 5173)              │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Static File Server                        │  │
│  │  • Serves /static/index.html                      │  │
│  │  • Serves /static/assets/*.js, *.css             │  │
│  │  • SPA routing (all routes → index.html)          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Reverse Proxy                             │  │
│  │  • /graphql → http://localhost:8000/graphql      │  │
│  │  • /api/*   → http://localhost:8000/api/*        │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           alphatrion server (port 8000)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │         GraphQL API                               │  │
│  │  • /graphql - Strawberry GraphQL endpoint        │  │
│  │  • Teams, Projects, Experiments, Runs, Metrics   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Artifact API                              │  │
│  │  • /api/artifacts/* - ORAS registry proxy        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Usage Patterns

### Pattern 1: Standard Usage (Recommended)

**With built-in proxy** - Easiest for development and testing:

```bash
# Terminal 1: Start backend
alphatrion server --port 8000

# Terminal 2: Start dashboard with proxy
alphatrion dashboard --port 5173
```

Access at: `http://localhost:5173`

The dashboard proxies all `/graphql` and `/api/*` requests to the backend.


### Pattern 2: Custom Backend URL

**Connect to remote backend:**

```bash
alphatrion dashboard --backend-url http://production-server:8000
```

This proxies requests to a different backend server.

## Command Options

```bash
alphatrion dashboard [OPTIONS]

Options:
  --port PORT              Port to run dashboard on (default: 5173)
  --backend-url URL        Backend server URL to proxy to (default: http://localhost:8000)
```

## Development vs Production

### Development

Use Vite's dev server for hot reload:

```bash
cd dashboard
npm run dev  # Runs on port 5173 with proxy configured in vite.config.ts
```

Vite config already includes proxy for `/graphql` and `/api`.

### Production

Two options:

**Option A: Using alphatrion dashboard command**
```bash
# Build once
cd dashboard && npm run build

# Run anytime
alphatrion dashboard
```

**Option B: Using a proper web server**
```bash
# Build with backend URL
cd dashboard
VITE_GRAPHQL_URL=http://api.example.com/graphql npm run build

# Serve with nginx/apache
nginx -c /path/to/nginx.conf
```

## Why Not Always Use Vite Dev Server?

The `alphatrion dashboard` command is for **convenience** when:
- You want to quickly view the dashboard
- You don't need hot reload
- You want everything in one command
- You're testing or demoing

For **active development**, use `npm run dev` which provides:
- Hot module replacement (instant updates)
- Better error messages
- Source maps
- Faster builds

## Common Issues

### Issue: Blank page

**Cause:** Static files not found or backend not running

**Solution:**
1. Build dashboard: `cd dashboard && npm run build`
2. Start backend: `alphatrion server`
3. Start dashboard: `alphatrion dashboard`

### Issue: "Backend server not available"

**Cause:** Backend not running or wrong URL

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/graphql

# Or start backend
alphatrion server --port 8000
```

## Summary

The **built-in proxy is a feature, not a bug**. It provides:
- ✅ Simple single-command deployment
- ✅ No CORS configuration needed
- ✅ Works with pre-built dashboard
- ✅ Similar to Vite's dev proxy

For production deployments, consider using nginx or another dedicated web server with proper caching, SSL, and load balancing.
