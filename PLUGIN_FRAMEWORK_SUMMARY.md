# Plugin Framework Summary

## What Was Created

I've designed and implemented a complete plugin framework for Alphatrion with the following characteristics:

### ✅ Framework Features

1. **Sidebar Integration** - Plugins appear as navigation items in the sidebar
2. **Full-Page Routes** - Each plugin gets its own route and full-page UI
3. **Complete Isolation** - Plugin code in separate folders, doesn't impact core
4. **Backend APIs** - Plugins can expose FastAPI endpoints
5. **Dynamic Discovery** - Plugins automatically appear when registered
6. **Clean Architecture** - Framework-first design for easy extension

## File Structure

```
alphatrion/
├── plugins/
│   ├── __init__.py              ✅ Plugin system exports
│   ├── base.py                  ✅ Plugin base class & registry
│   ├── registry.py              ✅ Global registry singleton
│   │
│   └── cloud_ide/              ✅ Example plugin
│       ├── __init__.py
│       ├── plugin.py           ✅ CloudIDE implementation
│       └── README.md           (to be added)
│
├── server/graphql/
│   ├── schema.py               ✅ Added plugins query
│   ├── types.py                ✅ Added PluginInfo type
│   └── resolvers.py            ✅ Added list_plugins resolver
│
└── PLUGIN_SYSTEM_V2.md         ✅ Complete documentation

dashboard/src/
├── types/index.ts              ✅ Added PluginInfo interface
├── lib/graphql-client.ts       ✅ Added listPlugins query
│
├── pages/plugins/              (to be created)
│   └── cloud-ide.tsx           (example plugin page)
│
└── components/layout/
    └── sidebar.tsx             (needs update to show plugins)
```

## Quick Start: Adding a Plugin

### 1. Create Plugin Backend (5 minutes)

```bash
# Create plugin folder
mkdir -p alphatrion/plugins/my_plugin
```

```python
# alphatrion/plugins/my_plugin/plugin.py
from alphatrion.plugins.base import Plugin, PluginMetadata
from fastapi import APIRouter

class MyPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-plugin",
            name="My Plugin",
            description="What it does",
            icon="Package",  # Lucide icon
            route="/my-plugin",
            sidebar_position=20,
            version="1.0.0",
            enabled=True,
        )

    def initialize(self, config=None):
        self._router = APIRouter(prefix="/api/plugins/my-plugin")

        @self._router.get("/")
        async def index():
            return {"message": "Hello!"}

    def get_api_router(self):
        return self._router
```

### 2. Register Plugin (1 minute)

```python
# In alphatrion/storage/runtime.py (or app.py)
from alphatrion.plugins import register_plugin
from alphatrion.plugins.my_plugin import MyPlugin

def init():
    # ... existing code ...

    # Register plugin
    plugin = MyPlugin()
    plugin.initialize()
    register_plugin(plugin)
```

### 3. Mount Plugin Routes (1 minute)

```python
# In alphatrion/server/cmd/app.py
from alphatrion.plugins import get_registry

# After creating FastAPI app
registry = get_registry()
for plugin in registry.list_enabled():
    router = plugin.get_api_router()
    if router:
        app.include_router(router)
```

### 4. Create Frontend Page (10 minutes)

```tsx
// dashboard/src/pages/plugins/my-plugin.tsx
export function MyPluginPage() {
  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold">My Plugin</h1>
      {/* Your custom UI */}
    </div>
  );
}
```

```tsx
// dashboard/src/App.tsx
import { MyPluginPage } from './pages/plugins/my-plugin';

// Add to routes
{ path: '/my-plugin', element: <MyPluginPage /> }
```

### 5. Update Sidebar (5 minutes)

```tsx
// dashboard/src/components/layout/sidebar.tsx
import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../../lib/graphql-client';
import * as Icons from 'lucide-react';

// In your sidebar component
const { data: plugins } = useQuery({
  queryKey: ['plugins'],
  queryFn: async () => {
    const result = await graphqlQuery(queries.listPlugins);
    return result.plugins;
  }
});

// Render plugin navigation items
{plugins?.map((plugin) => {
  const Icon = Icons[plugin.icon] || Icons.Package;
  return (
    <NavItem
      key={plugin.id}
      icon={Icon}
      to={plugin.route}
      label={plugin.name}
    />
  );
})}
```

### 6. Build & Test

```bash
cd dashboard
npm run build
cd ..
# Restart server
# Navigate to http://localhost:8000/my-plugin
```

## Key Concepts

### Plugin Metadata

Controls how the plugin appears:

```python
PluginMetadata(
    id="my-plugin",          # Unique ID (kebab-case)
    name="My Plugin",         # Shown in sidebar
    icon="Package",           # Lucide-react icon
    route="/my-plugin",       # Frontend route
    sidebar_position=20,      # Lower = higher in sidebar
    enabled=True,             # Show/hide plugin
)
```

### Plugin Isolation

✅ **Correct (Isolated)**
```
alphatrion/plugins/my_plugin/
├── plugin.py
├── models.py
├── utils.py
└── __init__.py

dashboard/src/pages/plugins/
└── my-plugin.tsx
```

❌ **Wrong (Mixed with core)**
```
alphatrion/server/my_plugin_api.py
dashboard/src/components/my-plugin-widget.tsx
```

### Plugin APIs

Plugins expose their own API endpoints:

```python
def initialize(self):
    self._router = APIRouter(prefix="/api/plugins/my-plugin")

    @self._router.get("/items")
    async def list_items():
        return {"items": [...]}

    @self._router.post("/items")
    async def create_item(item: Item):
        return {"id": "new-item"}
```

Frontend calls them:

```tsx
const response = await fetch('/api/plugins/my-plugin/items');
const data = await response.json();
```

### Full-Page Custom UI

Plugins can have completely custom styling:

```tsx
export function MyPluginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 to-blue-900">
      {/* Completely custom design */}
      <CustomHeader />
      <CustomSidebar />
      <CustomEditor />
      <CustomTerminal />
    </div>
  );
}
```

## Example: CloudIDE Plugin

See `alphatrion/plugins/cloud_ide/` for a complete example:

**Backend:**
- Metadata with Code icon
- API endpoints for IDE operations
- Returns `/cloud-ide` route

**Frontend** (to be created):
- Full-page code editor
- File tree
- Terminal
- Custom dark theme

**Sidebar:**
- Shows "Cloud IDE" with code icon
- Clicking navigates to `/cloud-ide`

## Next Steps

1. **Update Sidebar Component** - Add plugin navigation rendering
2. **Create CloudIDE Frontend** - Build example plugin UI
3. **Test Plugin System** - Create a simple test plugin
4. **Add More Examples** - Jupyter, Monitoring, etc.

## Documentation

- **PLUGIN_SYSTEM_V2.md** - Complete documentation (architecture, API, examples)
- **This file** - Quick reference and summary

## Architecture Benefits

✅ **Clean Separation** - Plugins don't touch core code
✅ **Easy to Add** - ~5 steps to add a new plugin
✅ **Flexible UI** - Full page = full creative control
✅ **Scalable** - Add unlimited plugins without complexity
✅ **Type Safe** - TypeScript + GraphQL types
✅ **Discoverable** - Automatic sidebar integration

## Migration from v1

The old system had plugins per-experiment. The new system has global plugins in sidebar.

**v1 (Old):**
- Plugins shown as cards in experiment detail
- Enabled per-experiment via metadata
- Opens in popup/new tab

**v2 (New):**
- Plugins shown in sidebar navigation
- Global (not per-experiment)
- Full-page routes

If you need per-experiment features, implement inside the plugin page (e.g., CloudIDE can list experiments and let you select one).

## Questions?

See `PLUGIN_SYSTEM_V2.md` for comprehensive documentation including:
- Detailed API reference
- Best practices
- Troubleshooting guide
- Advanced features
- Example code
