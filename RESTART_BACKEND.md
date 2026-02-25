# Backend Restart Required

After adding the `openInNewTab` field to the `PluginInfo` GraphQL type, the backend server must be restarted for Strawberry to regenerate the schema.

## Steps to Restart

### 1. Stop Backend Server

If running with `alphatrion server`:
```bash
# Press Ctrl+C in the terminal running the server
```

If running as a background process:
```bash
# Find the process
ps aux | grep "alphatrion server"

# Kill it
kill <PID>
```

### 2. Restart Backend Server

```bash
alphatrion server
```

The server should start and output:
```
Starting AlphaTrion server at http://0.0.0.0:8000
```

### 3. Verify GraphQL Schema

Test the query in your browser:
```
http://localhost:8000/graphql
```

Run this query:
```graphql
query {
  plugins {
    id
    name
    openInNewTab
  }
}
```

Expected response:
```json
{
  "data": {
    "plugins": [
      {
        "id": "cloud-ide",
        "name": "Cloud IDE",
        "openInNewTab": true
      }
    ]
  }
}
```

### 4. Clear Frontend Cache

If the sidebar still doesn't show the Cloud IDE:

**Option 1: Hard Refresh**
- Chrome/Firefox: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Safari: `Cmd+Option+R`

**Option 2: Clear Browser Cache**
- Open DevTools (F12)
- Right-click refresh button → "Empty Cache and Hard Reload"

**Option 3: Restart Dev Server**
```bash
cd dashboard
# Stop with Ctrl+C
npm run dev
```

### 5. Rebuild Dashboard (if in production)

If using the built dashboard:
```bash
cd dashboard
npm run build
```

Then restart the dashboard command:
```bash
alphatrion dashboard --userid <your-user-id>
```

## Verification Checklist

- [ ] Backend server restarted
- [ ] GraphQL query returns `openInNewTab` field
- [ ] Frontend cache cleared
- [ ] Cloud IDE appears in sidebar
- [ ] Clicking Cloud IDE opens new tab

## Troubleshooting

### Error: "Cannot query field 'openInNewTab'"

**Cause**: Backend not restarted or schema not updated

**Solution**:
1. Confirm changes in `alphatrion/server/graphql/types.py`
2. Confirm changes in `alphatrion/plugins/base.py`
3. Restart backend server
4. Check GraphQL playground

### Cloud IDE Not in Sidebar

**Cause 1**: Frontend query not updated

**Check**: `dashboard/src/lib/graphql-client.ts`
```typescript
listPlugins: `
  query ListPlugins {
    plugins {
      ...
      openInNewTab  // This line must be present
    }
  }
`
```

**Cause 2**: Query failed due to field error

**Check**: Browser console for GraphQL errors
1. Open DevTools (F12)
2. Go to Console tab
3. Look for GraphQL errors
4. If present, restart backend

**Cause 3**: Plugin not registered

**Check**: `alphatrion/storage/runtime.py`
```python
def _init_plugins():
    from alphatrion.plugins.workspace import WorkspacePlugin

    cloud_ide = WorkspacePlugin()
    cloud_ide.initialize()
    register_plugin(cloud_ide)
```

### Field Returns `null` Instead of `true`

**Cause**: Plugin metadata not updated

**Check**: `alphatrion/plugins/workspace/plugin.py`
```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        id="cloud-ide",
        name="Cloud IDE",
        # ...
        open_in_new_tab=True,  # This line must be present
    )
```

## Quick Reset Script

Save this as `restart-alphatrion.sh`:
```bash
#!/bin/bash

echo "🛑 Stopping backend..."
pkill -f "alphatrion server" || true

echo "🔄 Restarting backend..."
alphatrion server &
BACKEND_PID=$!

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "⏳ Waiting for backend to be ready..."
sleep 3

echo "🧪 Testing GraphQL schema..."
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ plugins { id name openInNewTab } }"}' \
  | python3 -m json.tool

echo ""
echo "✅ Backend ready!"
echo "🌐 GraphQL: http://localhost:8000/graphql"
echo "📊 Dashboard: Start with 'alphatrion dashboard --userid <id>'"
```

Usage:
```bash
chmod +x restart-alphatrion.sh
./restart-alphatrion.sh
```

## Summary

The `openInNewTab` field has been added to:
- ✅ Plugin base class (`alphatrion/plugins/base.py`)
- ✅ Workspace plugin metadata (`alphatrion/plugins/workspace/plugin.py`)
- ✅ GraphQL type (`alphatrion/server/graphql/types.py`)
- ✅ GraphQL resolver (`alphatrion/server/graphql/resolvers.py`)
- ✅ Frontend query (`dashboard/src/lib/graphql-client.ts`)
- ✅ Frontend types (`dashboard/src/types/index.ts`)
- ✅ Sidebar component (`dashboard/src/components/layout/sidebar.tsx`)

**Required action**: Restart backend server for schema to take effect.
