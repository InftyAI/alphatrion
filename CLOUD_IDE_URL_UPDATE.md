# Cloud IDE URL Updated

The Cloud IDE is now served at `/api/plugins/cloud-ide/ide` instead of static HTML files.

## Changes Made

### 1. Backend API Endpoint

Added endpoint to serve IDE HTML in `alphatrion/plugins/workspace/plugin.py`:

```python
@self._router.get("/ide")
async def serve_ide():
    """Serve the Cloud IDE HTML page."""
    # Find the dashboard static directory
    current_file = FilePath(__file__).resolve()
    possible_paths = [
        current_file.parents[4] / "dashboard" / "static" / "ide.html",
        FilePath.cwd() / "dashboard" / "static" / "ide.html",
        FilePath.cwd() / "static" / "ide.html",
    ]

    for path in possible_paths:
        if path.exists():
            return FileResponse(path)

    raise HTTPException(status_code=404, detail="IDE not found")
```

### 2. Sidebar Link Updated

Changed sidebar to use API endpoint in `dashboard/src/components/layout/sidebar.tsx`:

**Before:**
```typescript
const ideUrl = import.meta.env.DEV
  ? '/ide.html'
  : '/static/ide.html';
```

**After:**
```typescript
const ideUrl = '/api/plugins/cloud-ide/ide';
```

### 3. App Routes Cleaned Up

Removed unnecessary route in `dashboard/src/App.tsx`:

**Before:**
```typescript
<Route path="cloud-ide" element={<WorkspacePage />} />
```

**After:**
```typescript
{/* Plugin routes - Cloud IDE opens in new tab, no route needed */}
```

## How It Works

### User Flow

1. User clicks "Cloud IDE" in sidebar
2. Browser opens new tab with URL: `/api/plugins/cloud-ide/ide`
3. Backend serves `ide.html` from static directory
4. IDE loads with all its assets
5. User can work in full-screen IDE

### URL Structure

**Production:**
```
http://localhost:8000/api/plugins/cloud-ide/ide
```

**Development (with dashboard proxy):**
```
http://localhost:5173/api/plugins/cloud-ide/ide
↓ (proxied to)
http://localhost:8000/api/plugins/cloud-ide/ide
```

## Benefits

### 1. Consistent URL Pattern
- Follows plugin API convention: `/api/plugins/{plugin-id}/{endpoint}`
- Easy to remember
- Consistent with other plugin endpoints

### 2. Server-Side Control
- Backend controls IDE serving logic
- Can add authentication checks
- Can customize based on user context
- Can log IDE access

### 3. Future Enhancements

**Pass Parameters:**
```
/api/plugins/cloud-ide/ide?experimentId=123
/api/plugins/cloud-ide/ide?pod=my-pod
```

**Authentication:**
```python
@self._router.get("/ide")
async def serve_ide(request: Request):
    # Check if user is authenticated
    # Load user preferences
    # Customize IDE based on context
    return FileResponse(ide_path)
```

**Dynamic Content:**
```python
@self._router.get("/ide")
async def serve_ide(experimentId: str | None = None):
    # Read ide.html
    # Inject experiment context
    # Return customized HTML
    return HTMLResponse(customized_html)
```

## File Structure

```
alphatrion/
├── alphatrion/
│   └── plugins/
│       └── workspace/
│           └── plugin.py          # Serves IDE at /api/plugins/cloud-ide/ide
└── dashboard/
    ├── ide.html                    # Source HTML
    ├── static/
    │   └── ide.html               # Built HTML (served by backend)
    └── src/
        └── main-ide.tsx           # IDE React app
```

## Testing

### 1. Start Backend
```bash
alphatrion server
```

### 2. Build Dashboard
```bash
cd dashboard
npm run build
```

### 3. Test Direct Access
Open browser to:
```
http://localhost:8000/api/plugins/cloud-ide/ide
```

Expected: IDE loads in full screen

### 4. Test Sidebar Click
1. Open dashboard: `http://localhost:8000/`
2. Click "Cloud IDE" in sidebar
3. Expected: New tab opens with IDE

## Troubleshooting

### IDE Returns 404

**Symptom:** `/api/plugins/cloud-ide/ide` returns 404

**Causes:**
1. Dashboard not built (`npm run build`)
2. Backend can't find `ide.html` file
3. Plugin not initialized

**Solutions:**
1. Build dashboard: `cd dashboard && npm run build`
2. Verify `static/ide.html` exists
3. Restart backend: `alphatrion server`

### IDE Loads But Assets Missing

**Symptom:** IDE HTML loads but CSS/JS fail to load

**Cause:** Asset paths wrong in HTML

**Solution:** Rebuild dashboard with correct base path

### Sidebar Still Opens Old URL

**Symptom:** Clicking sidebar opens `/ide.html` or `/static/ide.html`

**Cause:** Frontend not rebuilt or browser cache

**Solutions:**
1. Rebuild: `cd dashboard && npm run build`
2. Hard refresh: Ctrl+Shift+R
3. Clear browser cache

## Migration from Static Files

**Old approach:**
- Sidebar links to `/ide.html` (dev) or `/static/ide.html` (prod)
- Static file server handles request
- Environment-dependent URLs

**New approach:**
- Sidebar links to `/api/plugins/cloud-ide/ide`
- Plugin backend handles request
- Single URL for all environments
- More control and flexibility

## Next Steps

The IDE is now served at the correct URL. To implement the full trial page UI, see:
- `CLOUD_IDE_FULL_MIGRATION_PLAN.md` - Complete migration plan
- Estimated 18-28 hours to migrate all trial page features
- Includes evolution charts, lineage, content snapshots, etc.

Current status:
- ✅ URL structure updated
- ✅ Backend endpoint created
- ✅ Sidebar integration complete
- ✅ Opens in new tab
- ⏳ Full trial page UI (pending - see migration plan)
