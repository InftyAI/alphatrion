# Cloud IDE Blank Page Fix

## Issue
The Cloud IDE was showing a blank page when accessed at `http://127.0.0.1:5173/api/plugins/cloud-ide/ide`

## Root Causes

### 1. Wrong URL in Development Mode
**Problem:** Sidebar was using `/api/plugins/cloud-ide/ide` for both dev and production
- In **production**: Backend serves the IDE at `/api/plugins/cloud-ide/ide` ✓
- In **development**: Vite dev server doesn't proxy this route ✗

**Solution:** Updated sidebar to use environment-specific URLs:
```typescript
// In dev mode, use /ide.html; in production, use API endpoint
const ideUrl = import.meta.env.DEV
  ? '/ide.html'
  : '/api/plugins/cloud-ide/ide';
```

### 2. Missing User and Team Context Initialization
**Problem:** The IDE entry point (`main-ide.tsx`) didn't initialize:
- User authentication
- Team context
- Team selection

This caused the CloudIDEFull component to fail when calling `useTeamContext()` which returned `null`.

**Solution:** Added initialization logic to `main-ide.tsx`:
```typescript
function IDEApp() {
  // Initialize user
  const userId = await getUserId();
  const userData = await graphqlQuery(queries.getUser, { id: userId });
  setCurrentUser(userData.user);

  // Initialize team
  const teamsData = await graphqlQuery(queries.listTeams, { userId });
  setSelectedTeamId(teamsData.teams[0].id, userId);
}
```

## Changes Made

### 1. `src/components/layout/sidebar.tsx`
Updated plugin link to use correct URL based on environment:
```typescript
if (plugin.openInNewTab) {
  const ideUrl = import.meta.env.DEV ? '/ide.html' : '/api/plugins/cloud-ide/ide';
  return <a href={ideUrl} target="_blank" ...>{plugin.name}</a>;
}
```

### 2. `src/main-ide.tsx`
Added complete initialization wrapper:
- Fetches user ID from config
- Loads user data via GraphQL
- Loads and auto-selects team
- Provides UserProvider and TeamProvider contexts
- Shows loading spinner during initialization
- Shows error message if initialization fails

## Testing

### Development Mode

1. **Start dev server:**
   ```bash
   cd dashboard
   npm run dev
   ```

2. **Open dashboard:**
   ```
   http://localhost:5173
   ```

3. **Click "Cloud IDE" in sidebar:**
   - Should open new tab at: `http://localhost:5173/ide.html`
   - Should show: "Loading Cloud IDE..." spinner
   - Then show: Project and experiment selectors

### Production Mode

1. **Build dashboard:**
   ```bash
   cd dashboard
   npm run build
   ```

2. **Start backend:**
   ```bash
   alphatrion server
   ```

3. **Open dashboard:**
   ```
   http://localhost:8000
   ```

4. **Click "Cloud IDE" in sidebar:**
   - Should open new tab at: `http://localhost:8000/api/plugins/cloud-ide/ide`
   - Backend serves `static/ide.html`
   - Should show: Project and experiment selectors

## Expected Behavior

### Initial Load
```
┌─────────────────────────────────────┐
│        ⏳ Loading Cloud IDE...       │
└─────────────────────────────────────┘
```

### After Loading
```
┌──────────────────────────────────────────────────────────┐
│ Project: [MyProject ▼]  Experiment: [Select...▼]  Status: - │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Please select a project and experiment to get started. │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### After Selecting Experiment
```
┌──────────────────────────────────────────────────────────┐
│ Project: [MyProject ▼]  Experiment: [Exp-123 ▼]  ● RUNNING │
├─────────┬──────────────────────────┬─────────────────────┤
│ Files   │ Code Viewer              │ Evolution Chart     │
│ • src/  │                          │                     │
│   └─main│ def train():            │    ●                │
│ • tests/│   model = Model()       │      ● ●            │
└─────────┴──────────────────────────┴─────────────────────┘
```

## Troubleshooting

### Still seeing blank page?

1. **Check browser console** (F12 → Console tab):
   - Look for errors related to GraphQL, user, or team
   - Common errors:
     - "User not found" → Backend not running or wrong user ID
     - "Failed to fetch" → Backend not accessible
     - Network errors → Check proxy configuration

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/graphql
   # Should return: Method Not Allowed (GET not supported)
   ```

3. **Check user ID configuration:**
   ```bash
   # If using environment variable
   echo $ALPHATRION_USER_ID

   # Or check in dashboard config
   cat dashboard/.env
   ```

4. **Hard refresh browser:**
   - Chrome/Edge: Ctrl + Shift + R
   - Firefox: Ctrl + F5
   - Safari: Cmd + Shift + R

5. **Clear browser cache:**
   - Settings → Privacy → Clear browsing data
   - Select "Cached images and files"

### Error: "useTeamContext must be used within TeamProvider"

This should be fixed now. If you still see it:
- Verify `main-ide.tsx` was updated
- Check that TeamProvider wraps IDEApp
- Rebuild: `npm run build`

### Loading spinner never completes

Check:
1. Backend GraphQL endpoint is responding
2. User ID exists in database
3. User has at least one team
4. Network tab shows successful GraphQL responses

## Summary

The blank page was caused by:
1. ❌ Using production URL (`/api/plugins/cloud-ide/ide`) in dev mode
2. ❌ Missing user/team initialization in IDE entry point

Fixed by:
1. ✅ Using `/ide.html` in dev, `/api/plugins/cloud-ide/ide` in production
2. ✅ Adding full initialization logic to `main-ide.tsx`

Now the IDE properly:
- ✅ Loads in both dev and production modes
- ✅ Initializes user and team context
- ✅ Shows loading states
- ✅ Displays project/experiment selectors
- ✅ Renders full IDE interface
