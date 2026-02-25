# Cloud IDE Routing Fix

## Issue
Cloud IDE was showing blank page at `http://127.0.0.1:5173/plugins/cloud-ide`

## Root Cause
The route `/plugins/cloud-ide` was not defined in the React Router configuration. The Cloud IDE was only accessible via:
- `/ide.html` (separate HTML file)
- Not accessible via React Router

## Solution
Added a proper route for the Cloud IDE in the main App router that:
1. Renders CloudIDEFull component at `/plugins/cloud-ide`
2. Renders **outside** the Layout component (no sidebar/header)
3. Works in both development and production modes

## Changes Made

### 1. `src/App.tsx`
Added CloudIDEFull import and route:

```typescript
// Import
import CloudIDEFull from './pages/plugins/cloud-ide-full';

// Route configuration
<Routes>
  {/* Cloud IDE - standalone page without layout */}
  <Route path="/plugins/cloud-ide" element={<CloudIDEFull />} />

  {/* Main dashboard with layout */}
  <Route path="/" element={<Layout />}>
    {/* ... other routes ... */}
  </Route>
</Routes>
```

**Key Point:** The Cloud IDE route is **outside** the `<Layout />` component so it renders fullscreen without the sidebar.

### 2. `src/components/layout/sidebar.tsx`
Updated the URL to use the route in development:

```typescript
if (plugin.openInNewTab) {
  // Use /plugins/cloud-ide route in dev, API endpoint in production
  const ideUrl = import.meta.env.DEV
    ? '/plugins/cloud-ide'
    : '/api/plugins/cloud-ide/ide';

  return <a href={ideUrl} target="_blank" ...>{plugin.name}</a>;
}
```

## URL Structure

### Development Mode
```
http://localhost:5173/plugins/cloud-ide
                      └─ React Router handles this
```

**Flow:**
1. User clicks "Cloud IDE" in sidebar
2. Opens new tab at `/plugins/cloud-ide`
3. React Router matches the route
4. Renders `CloudIDEFull` component
5. Component initializes user/team context
6. Shows project/experiment selectors

### Production Mode
```
http://localhost:8000/api/plugins/cloud-ide/ide
                      └─ Backend serves static/ide.html
```

**Flow:**
1. User clicks "Cloud IDE" in sidebar
2. Opens new tab at `/api/plugins/cloud-ide/ide`
3. Backend serves pre-built `static/ide.html`
4. Browser loads and executes `ide-*.js`
5. Component initializes user/team context
6. Shows project/experiment selectors

## Architecture

### Main Dashboard (index.html)
```
┌─────────────────────────────────────┐
│ Layout (Sidebar + Header)          │
│ ┌─────────────────────────────────┐ │
│ │ Dashboard / Projects / Etc.     │ │
│ │                                 │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Cloud IDE (standalone route)
```
┌─────────────────────────────────────┐
│ CloudIDEFull (No Layout)            │
│ ┌───────────────────────────────┐   │
│ │ Project/Experiment Selectors  │   │
│ ├────┬──────────────┬───────────┤   │
│ │    │              │           │   │
│ │    │              │           │   │
│ └────┴──────────────┴───────────┘   │
└─────────────────────────────────────┘
```

## Testing

### Development Mode

1. **Start dev server:**
   ```bash
   cd dashboard
   npm run dev
   ```

2. **Navigate to:**
   ```
   http://localhost:5173/plugins/cloud-ide
   ```

3. **Or click "Cloud IDE" in sidebar:**
   - Opens new tab
   - URL: `http://localhost:5173/plugins/cloud-ide`
   - Should show: Project and experiment selectors

### Production Mode

1. **Build and start:**
   ```bash
   cd dashboard
   npm run build
   cd ..
   alphatrion server
   ```

2. **Click "Cloud IDE" in sidebar:**
   - Opens new tab
   - URL: `http://localhost:8000/api/plugins/cloud-ide/ide`
   - Backend serves static HTML
   - Should show: Project and experiment selectors

## Comparison: Three Ways to Access Cloud IDE

### Option 1: React Router (Development) ✅
```
URL: /plugins/cloud-ide
Method: React Router matches route
Context: Shared with main app
Works: Development only
```

### Option 2: Separate HTML (Development)
```
URL: /ide.html
Method: Vite serves HTML file
Context: Separate initialization
Works: Development only
Note: Still functional but not recommended
```

### Option 3: Backend API (Production) ✅
```
URL: /api/plugins/cloud-ide/ide
Method: Backend serves static HTML
Context: Separate initialization
Works: Production only
```

## Benefits

1. **Clean URLs:** `/plugins/cloud-ide` is easier to remember than `/ide.html`
2. **Consistent routing:** Uses React Router like other pages
3. **Shared context:** Can share context with main app if needed
4. **No sidebar:** Renders fullscreen by being outside Layout
5. **Works in dev mode:** No need to build and run backend for testing

## Troubleshooting

### Still seeing blank page?

1. **Check the browser console (F12):**
   ```
   Look for errors like:
   - "User not found" → Backend not running
   - "Failed to fetch" → GraphQL endpoint down
   - "useTeamContext must be used within TeamProvider" → Context issue
   ```

2. **Verify the route is working:**
   ```bash
   # In browser, open DevTools → Network tab
   # Navigate to /plugins/cloud-ide
   # Should see:
   # - 200 OK for the route
   # - GraphQL queries succeeding
   ```

3. **Check user initialization:**
   ```typescript
   // Should see in console:
   console.log('Loading Cloud IDE...')
   // Then project/experiment selectors should appear
   ```

4. **Hard refresh:**
   - Chrome: Ctrl + Shift + R (Windows/Linux) or Cmd + Shift + R (Mac)
   - This clears cached JS/CSS

### Error: "Cannot GET /plugins/cloud-ide"

This means React Router is not handling the route. Causes:
- Dev server not running (`npm run dev`)
- Wrong base URL in vite.config.ts
- Route not added to App.tsx

### Route works but shows sidebar

The route must be **outside** the `<Layout />` component:

```typescript
// ✅ Correct
<Routes>
  <Route path="/plugins/cloud-ide" element={<CloudIDEFull />} />
  <Route path="/" element={<Layout />}>
    {/* other routes */}
  </Route>
</Routes>

// ❌ Wrong
<Routes>
  <Route path="/" element={<Layout />}>
    <Route path="/plugins/cloud-ide" element={<CloudIDEFull />} />
  </Route>
</Routes>
```

## Summary

Fixed blank page by:
1. ✅ Added `/plugins/cloud-ide` route to App.tsx
2. ✅ Placed route outside Layout for fullscreen rendering
3. ✅ Updated sidebar to use new route in dev mode
4. ✅ Maintained backward compatibility with production API endpoint

Now accessible at:
- **Dev:** http://localhost:5173/plugins/cloud-ide
- **Prod:** http://localhost:8000/api/plugins/cloud-ide/ide
