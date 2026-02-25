# Workspace Plugin Setup Guide

Complete guide to enable the Workspace plugin in Alphatrion.

## What is Workspace Plugin?

An AI development environment similar to Lightning.ai AI Studio with:
- 📁 File explorer and editor
- 💻 Integrated terminal
- 🔧 Python environment management
- 📊 Resource monitoring (CPU, memory, disk, GPU)

## Quick Setup (5 Steps)

### Step 1: Register the Plugin

Add to `alphatrion/storage/runtime.py` or your app initialization file:

```python
# alphatrion/storage/runtime.py
from alphatrion.plugins import register_plugin
from alphatrion.plugins.workspace import WorkspacePlugin
from alphatrion.plugins.cloud_ide import CloudIDEPlugin

class StorageRuntime:
    def __init__(self):
        # ... existing initialization ...

        # Register plugins
        self._init_plugins()

    def _init_plugins(self):
        """Initialize and register all plugins."""
        # CloudIDE plugin
        cloud_ide = CloudIDEPlugin()
        cloud_ide.initialize()
        register_plugin(cloud_ide)

        # Workspace plugin
        workspace = WorkspacePlugin()
        workspace.initialize({
            "workspace_root": "/path/to/workspace"  # Optional, defaults to ~/alphatrion-workspace
        })
        register_plugin(workspace)
```

### Step 2: Mount Plugin Routes

Add to `alphatrion/server/cmd/app.py`:

```python
# alphatrion/server/cmd/app.py
from fastapi import FastAPI
from alphatrion.plugins import get_registry

app = FastAPI()

# ... existing routes ...

# Mount plugin routes
def mount_plugin_routes():
    """Mount API routes for all registered plugins."""
    registry = get_registry()
    for plugin in registry.list_enabled():
        router = plugin.get_api_router()
        if router:
            app.include_router(router)
            print(f"Mounted routes for plugin: {plugin.get_metadata().name}")

# Call after storage runtime initialization
from alphatrion.storage import runtime
runtime.init()
mount_plugin_routes()
```

### Step 3: Add Frontend Route

Add to `dashboard/src/App.tsx` or your router configuration:

```tsx
// dashboard/src/App.tsx
import { WorkspacePage } from './pages/plugins/workspace';

// In your routes
const routes = [
  // ... existing routes ...
  {
    path: '/workspace',
    element: <WorkspacePage />
  },
];
```

### Step 4: Update Sidebar

Update `dashboard/src/components/layout/sidebar.tsx` to show plugins:

```tsx
// dashboard/src/components/layout/sidebar.tsx
import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../../lib/graphql-client';
import * as Icons from 'lucide-react';
import { NavLink } from 'react-router-dom';

function Sidebar() {
  // Fetch plugins from GraphQL
  const { data: plugins } = useQuery({
    queryKey: ['plugins'],
    queryFn: async () => {
      const result = await graphqlQuery(queries.listPlugins);
      return result.plugins;
    },
    staleTime: Infinity, // Plugins don't change often
  });

  return (
    <nav className="flex flex-col gap-1 p-2">
      {/* Core navigation items */}
      <NavLink to="/" className="nav-item">
        <Home className="h-4 w-4" />
        <span>Home</span>
      </NavLink>

      {/* Separator */}
      <div className="h-px bg-border my-2" />

      {/* Plugin navigation items */}
      {plugins?.map((plugin) => {
        const IconComponent = (Icons as any)[plugin.icon] || Icons.Package;
        return (
          <NavLink
            key={plugin.id}
            to={plugin.route}
            className="nav-item"
          >
            <IconComponent className="h-4 w-4" />
            <span>{plugin.name}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
```

### Step 5: Install Dependencies & Build

```bash
# Install Python dependencies
pip install psutil

# Build frontend
cd dashboard
npm run build
cd ..

# Restart server
python -m alphatrion.server.cmd.main server
```

## Verification

### Test Backend APIs

```bash
# Test file tree
curl http://localhost:8000/api/plugins/workspace/files/tree

# Test terminal
curl -X POST http://localhost:8000/api/plugins/workspace/terminal/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "echo Hello World"}'

# Test resources
curl http://localhost:8000/api/plugins/workspace/resources/status
```

### Test Frontend

1. Navigate to http://localhost:8000
2. Look for "Workspace" in sidebar
3. Click it to open workspace page
4. You should see:
   - File explorer on left
   - Editor/Terminal tabs in center
   - Resource monitor at bottom of sidebar

## Configuration Options

### Workspace Root Directory

```python
workspace.initialize({
    "workspace_root": "/custom/path/to/workspace"
})
```

Default: `~/alphatrion-workspace`

### Security Considerations

For production, consider:

```python
workspace.initialize({
    "workspace_root": "/safe/sandboxed/path",
    "max_file_size": 10 * 1024 * 1024,  # 10MB limit (future feature)
    "allowed_commands": ["python", "pip", "ls"],  # Command whitelist (future feature)
})
```

## File Structure After Setup

```
alphatrion/
├── plugins/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── cloud_ide/
│   │   ├── __init__.py
│   │   └── plugin.py
│   └── workspace/              ✅ NEW
│       ├── __init__.py
│       ├── plugin.py
│       └── README.md
│
├── storage/runtime.py          ✅ MODIFIED (register plugins)
└── server/cmd/app.py           ✅ MODIFIED (mount routes)

dashboard/src/
├── App.tsx                     ✅ MODIFIED (add route)
├── components/layout/
│   └── sidebar.tsx             ✅ MODIFIED (show plugins)
└── pages/plugins/
    └── workspace.tsx           ✅ NEW
```

## Usage Examples

### Example 1: Edit a Python File

1. Open workspace: `http://localhost:8000/workspace`
2. Click on `script.py` in file tree
3. Edit the code in the editor
4. Click "Save" button
5. File is saved to disk

### Example 2: Run a Script

1. Switch to "Terminal" tab
2. Type: `python script.py`
3. Press Enter
4. View output in terminal

### Example 3: Create New File

1. Click the "+" button in file explorer (if implemented)
2. Or use API:
   ```bash
   curl -X POST http://localhost:8000/api/plugins/workspace/files/create \
     -H "Content-Type: application/json" \
     -d '{"path": "test.py", "type": "file", "content": "print(\"Hello\")"}'
   ```
3. File appears in tree

### Example 4: Monitor Resources

Resources are automatically displayed in sidebar:
- CPU: 45%
- Memory: 8GB / 16GB (50%)
- Disk: 500GB / 1TB (50%)
- GPUs: 1 GPU detected

## Troubleshooting

### Plugin not in sidebar

**Problem:** Workspace doesn't appear in sidebar
**Solution:**
1. Check plugin is registered: `registry.list_enabled()`
2. Verify GraphQL query returns plugin
3. Rebuild frontend: `npm run build`
4. Hard refresh browser (Cmd+Shift+R)

### Cannot access workspace files

**Problem:** 403 Forbidden when accessing files
**Solution:**
1. Check workspace_root directory exists
2. Verify file permissions
3. Ensure path is within workspace_root

### Terminal commands not working

**Problem:** Commands return errors
**Solution:**
1. Check command is in PATH
2. Verify timeout isn't too short (default 30s)
3. Check server logs for detailed errors
4. Try simple command first: `echo test`

### Resource monitoring shows 0%

**Problem:** All resource metrics show 0 or error
**Solution:**
1. Install psutil: `pip install psutil`
2. Restart server
3. Check for permission issues

### Frontend build errors

**Problem:** TypeScript errors during build
**Solution:**
1. Check all imports are correct
2. Verify shadcn/ui components are installed
3. Run `npm install` to ensure dependencies
4. Check types in `src/types/index.ts`

## Advanced Features

### Custom File Operations

Add custom buttons to file tree:

```tsx
// In workspace.tsx
const createNewFile = async (path: string) => {
  await fetch('/api/plugins/workspace/files/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      path: path,
      type: 'file',
      content: '# New file\n'
    })
  });
  loadFileTree(); // Refresh
};
```

### Keyboard Shortcuts

Add keyboard shortcuts for common actions:

```tsx
useEffect(() => {
  const handleKeyPress = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      saveFile();
    }
  };
  window.addEventListener('keydown', handleKeyPress);
  return () => window.removeEventListener('keydown', handleKeyPress);
}, [saveFile]);
```

### Monaco Editor Integration

For better editing experience, integrate Monaco:

```bash
npm install @monaco-editor/react
```

```tsx
import Editor from '@monaco-editor/react';

<Editor
  height="100%"
  defaultLanguage="python"
  value={fileContent}
  onChange={(value) => setFileContent(value || '')}
  theme="vs-dark"
  options={{
    minimap: { enabled: false },
    fontSize: 13,
  }}
/>
```

## Next Steps

1. **Test the plugin** - Verify all features work
2. **Customize workspace root** - Set appropriate directory
3. **Add security** - Implement sandboxing for production
4. **Extend functionality** - Add Git integration, notebooks, etc.
5. **Monitor usage** - Track resource consumption

## Related Documentation

- `PLUGIN_SYSTEM_V2.md` - Complete plugin framework guide
- `alphatrion/plugins/workspace/README.md` - Workspace plugin details
- `PLUGIN_FRAMEWORK_SUMMARY.md` - Quick reference

## Support

For issues or questions:
1. Check this guide and related docs
2. Review plugin README
3. Check backend logs for errors
4. Open issue on GitHub

## Summary

The Workspace plugin provides a complete AI development environment accessible from the Alphatrion sidebar. After following these 5 steps, you'll have a fully functional workspace with file editing, terminal access, and resource monitoring - similar to Lightning.ai AI Studio!
