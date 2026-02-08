# AlphaTrion Dashboard CLI

## Overview

The AlphaTrion dashboard can be launched via the CLI command `alphatrion dashboard`. This command starts a local web server that serves the dashboard application and automatically opens it in your default browser.

## Prerequisites

Before running the dashboard, ensure the static files have been built:

```bash
cd dashboard
npm install
npm run build
```

## Usage

### Basic Usage

Launch the dashboard with default settings:

```bash
alphatrion dashboard
```

This will:
- Start the dashboard server on port 5173
- Automatically open your default browser to `http://127.0.0.1:5173`

### Custom Port

Run the dashboard on a different port:

```bash
alphatrion dashboard --port 8080
```

### Without Auto-Browser

Start the server without automatically opening a browser:

```bash
alphatrion dashboard --no-browser
```

This is useful when:
- Running on a remote server
- You want to manually open the browser
- Running in a CI/CD environment

## Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Port to run the dashboard on | 5173 |
| `--no-browser` | Don't automatically open browser | false |

## Examples

### Development Workflow

```bash
# Terminal 1: Build and watch dashboard changes
cd dashboard
npm run dev

# Terminal 2: Run the AlphaTrion server
alphatrion server --port 8000

# Terminal 3: Launch dashboard
alphatrion dashboard --port 5173
```

### Production Deployment

```bash
# Build the dashboard
cd dashboard
npm run build

# Launch dashboard on custom port without browser
alphatrion dashboard --port 3000 --no-browser
```

## Troubleshooting

### Error: Dashboard static files not found

If you see this error:

```
❌ Error: Dashboard static files not found!
Please ensure the dashboard has been built by running:
  cd dashboard && npm run build
```

**Solution**: Build the dashboard first:

```bash
cd dashboard
npm install
npm run build
```

### Port Already in Use

If port 5173 is already in use, specify a different port:

```bash
alphatrion dashboard --port 5174
```

### Dashboard Not Opening in Browser

If the browser doesn't open automatically:

1. Check if `--no-browser` flag was set
2. Manually open your browser and navigate to `http://127.0.0.1:5173`
3. Check if the server started successfully in the terminal output

## Architecture

The dashboard command:

1. **Locates static files**: Searches multiple possible locations for the built dashboard
2. **Creates FastAPI app**: Sets up a simple web server
3. **Serves SPA**: All routes fallback to `index.html` for client-side routing
4. **Opens browser**: Automatically launches default browser (unless `--no-browser`)
5. **Serves assets**: Static assets (JS, CSS, images) from `/assets` directory

## Related Commands

- `alphatrion server` - Run the AlphaTrion GraphQL API server
- `alphatrion version` - Show AlphaTrion version
