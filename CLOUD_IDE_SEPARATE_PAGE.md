# Cloud IDE as Separate Page

The Cloud IDE now opens in a completely separate browser tab/window, independent of the AlphaTrion dashboard layout. This provides a full-screen IDE experience without the dashboard navigation.

## Architecture

### Multi-Page Application Setup

The project uses Vite's multi-page application feature to build two separate entry points:

1. **Main Dashboard** (`index.html`) - AlphaTrion dashboard with navigation
2. **Cloud IDE** (`ide.html`) - Standalone full-screen IDE

### File Structure

```
dashboard/
├── index.html              # Main dashboard entry point
├── ide.html                # Cloud IDE entry point (new)
├── src/
│   ├── main.tsx            # Dashboard app entry
│   ├── main-ide.tsx        # IDE app entry (new)
│   ├── App.tsx             # Dashboard routes
│   └── pages/plugins/
│       ├── workspace.tsx   # Workspace selector (launches IDE)
│       └── cloud-ide-full.tsx  # Full IDE implementation
```

### Build Configuration

**vite.config.ts:**
```typescript
build: {
  outDir: "./static",
  rollupOptions: {
    input: {
      main: path.resolve(__dirname, "index.html"),
      ide: path.resolve(__dirname, "ide.html"),
    },
  },
}
```

This configuration builds:
- `static/index.html` - Main dashboard
- `static/ide.html` - Cloud IDE
- Shared assets (CSS, JS chunks)

## Usage

### From Workspace Page

The Cloud IDE workspace page (`/cloud-ide` in dashboard) provides two options:

**1. Local Workspace**
```tsx
const openLocalWorkspace = () => {
  const ideUrl = import.meta.env.DEV
    ? '/ide.html'
    : '/static/ide.html';
  window.open(ideUrl, '_blank', 'width=1400,height=900');
};
```

**2. K8s Pod Workspace**
```tsx
const openPodWorkspace = (podName: string) => {
  const ideUrl = import.meta.env.DEV
    ? `/ide.html?pod=${podName}`
    : `/static/ide.html?pod=${podName}`;
  window.open(ideUrl, '_blank', 'width=1400,height=900');
};
```

### URL Patterns

**Development (Vite dev server):**
- Dashboard: `http://localhost:5173/`
- Local IDE: `http://localhost:5173/ide.html`
- K8s IDE: `http://localhost:5173/ide.html?pod=cloud-ide-my-pod`

**Production (alphatrion dashboard command):**
- Dashboard: `http://localhost:8000/`
- Local IDE: `http://localhost:8000/static/ide.html`
- K8s IDE: `http://localhost:8000/static/ide.html?pod=cloud-ide-my-pod`

## Implementation Details

### main-ide.tsx

The IDE entry point initializes a minimal React app without the dashboard layout:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { CloudIDEFull } from './pages/plugins/cloud-ide-full';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TeamProvider>
        <BrowserRouter>
          <CloudIDEFull />
        </BrowserRouter>
      </TeamProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
```

**Key Differences from main.tsx:**
- No `Layout` component (no sidebar/header)
- No `UserProvider` (not needed for IDE)
- Direct rendering of `CloudIDEFull` component
- Minimal setup for faster loading

### CloudIDEFull Component

The IDE reads URL parameters to determine mode:

```tsx
export function CloudIDEFull() {
  const { experimentId } = useParams<{ experimentId?: string }>();
  const [searchParams] = useSearchParams();
  const podName = searchParams.get('pod');

  // Determine mode based on pod parameter
  const mode: WorkspaceMode = podName ? 'k8s' : 'local';

  // ... rest of component
}
```

### Workspace Page Updates

The workspace page now acts as a launcher for the IDE:

**Before:**
- Navigated to `/cloud-ide` within dashboard
- Used dashboard layout and routing

**After:**
- Opens IDE in new window/tab
- Provides mode selection (local/K8s)
- Manages pod lifecycle
- Launch buttons for each workspace

## Benefits

### 1. Isolated Experience
- **Full Screen**: IDE uses entire browser window
- **No Distractions**: No dashboard navigation clutter
- **Better Focus**: Dedicated workspace for coding

### 2. Multi-Instance Support
- **Multiple IDEs**: Open different workspaces simultaneously
- **Side-by-Side**: Compare code across experiments
- **Pod Management**: Each pod gets its own IDE window

### 3. Performance
- **Faster Loading**: IDE doesn't load dashboard components
- **Smaller Bundle**: `ide.js` is separate from `main.js`
- **Better Caching**: Dashboard and IDE can be cached independently

### 4. Flexibility
- **Bookmarkable**: Direct URL to IDE with pod parameter
- **Shareable**: Send IDE link to team members
- **External Tools**: Open IDE from external scripts

## Development Workflow

### Running in Development

**Terminal 1 - Backend:**
```bash
alphatrion server
```

**Terminal 2 - Dashboard:**
```bash
cd dashboard
npm run dev
```

Access:
- Dashboard: `http://localhost:5173/`
- IDE: `http://localhost:5173/ide.html`

### Building for Production

```bash
cd dashboard
npm run build
```

Outputs:
```
static/
├── index.html           # Dashboard
├── ide.html            # Cloud IDE
├── assets/
│   ├── index-*.css     # Shared styles
│   ├── ide-*.js        # IDE bundle
│   ├── main-*.js       # Dashboard bundle
│   └── index-*.js      # Shared code
```

### Serving in Production

**Option 1: alphatrion dashboard command**
```bash
alphatrion dashboard --userid <user-id>
```

Serves:
- `/` → `static/index.html` (dashboard)
- `/static/ide.html` → IDE
- `/static/*` → Static assets

**Option 2: Backend server with static files**

Add to `alphatrion/server/cmd/app.py`:
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="path/to/static", html=True), name="static")
```

## Browser Window Configuration

The IDE opens with specific window dimensions:

```typescript
window.open(ideUrl, '_blank', 'width=1400,height=900');
```

**Parameters:**
- `width=1400` - 1400px wide (good for 1080p screens)
- `height=900` - 900px tall (leaves space for OS taskbar)
- `_blank` - Open in new tab/window (browser preference)

**User Experience:**
- Modern browsers: Opens in new tab by default
- User setting: Can configure to open in new window
- Mobile: Opens in same tab (window.open behavior)

## Future Enhancements

### 1. Progressive Web App (PWA)
- Install IDE as standalone app
- Offline support
- Desktop icon
- Native-like experience

### 2. Multiple Workspaces
```typescript
// Open multiple pods simultaneously
pods.forEach(pod => {
  window.open(`/static/ide.html?pod=${pod.name}`, '_blank');
});
```

### 3. IDE State Persistence
- Save open files per workspace
- Remember panel layout
- Persist terminal history
- Sync across tabs

### 4. Window Management
- Save/restore window size and position
- Tile multiple IDE windows
- Master/detail layout
- Synchronized scrolling

### 5. Communication Between Windows
- Broadcast channel API for sync
- Share clipboard between IDEs
- Notify dashboard on file changes
- Real-time collaboration

## Troubleshooting

### IDE Opens in Same Tab

**Symptom**: IDE replaces dashboard instead of opening new window

**Cause**: Browser popup blocker or user preference

**Solution**:
1. Allow popups for the site
2. Or use right-click → "Open in new tab"

### Static Files Not Found (404)

**Symptom**: `/static/ide.html` returns 404

**Cause**: Static files not built or wrong path

**Solutions**:
1. Build the dashboard: `cd dashboard && npm run build`
2. Check `static/` directory exists
3. Verify `ide.html` is in `static/` folder
4. Restart dashboard server

### IDE Loads But Shows Errors

**Symptom**: IDE opens but shows "Cannot connect" errors

**Cause**: Backend API not accessible

**Solutions**:
1. Ensure backend is running: `alphatrion server`
2. Check backend URL in browser console
3. Verify API endpoints are accessible
4. Check browser console for CORS errors

### Window Size Too Small

**Symptom**: IDE window is too small or cramped

**Solution**: Adjust window.open parameters:
```typescript
window.open(ideUrl, '_blank', 'width=1920,height=1080');
```

### CSS Not Loading

**Symptom**: IDE has no styling

**Cause**: Shared CSS bundle not loading

**Solutions**:
1. Check browser console for failed CSS requests
2. Verify `index-*.css` exists in `static/assets/`
3. Clear browser cache
4. Rebuild: `npm run build`

## Summary

The Cloud IDE is now a standalone application that:

✅ Opens in a separate browser tab/window
✅ Provides full-screen IDE experience
✅ Loads independently from dashboard
✅ Supports both local and K8s workspaces
✅ Allows multiple concurrent IDE instances
✅ Uses multi-page Vite build configuration
✅ Has smaller bundle size than before
✅ Works in both development and production

Access the IDE by navigating to **`/cloud-ide`** in the dashboard and clicking "Open Local IDE" or "Open" next to a K8s pod.
