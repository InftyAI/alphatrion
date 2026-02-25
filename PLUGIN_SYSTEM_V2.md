# Alphatrion Plugin System v2

## Overview

The plugin system allows you to extend Alphatrion with isolated, modular functionality. Plugins appear in the sidebar navigation and provide full-page custom interfaces.

**Key Features:**
- 🎨 **Custom UI** - Each plugin defines its own full-page React component
- 🔌 **Isolated** - Plugin code in separate folders, doesn't impact core
- 🚀 **Backend APIs** - Plugins can expose their own FastAPI endpoints
- 📍 **Sidebar Navigation** - Automatic sidebar integration
- 🎯 **Framework-first** - Clean architecture for easy plugin development

## Architecture

```
alphatrion/
├── plugins/                           # Plugin system core
│   ├── __init__.py                   # Plugin exports
│   ├── base.py                       # Plugin & PluginRegistry
│   ├── registry.py                   # Global registry
│   │
│   └── cloud_ide/                    # Example plugin
│       ├── __init__.py
│       ├── plugin.py                 # Backend implementation
│       └── README.md                 # Plugin documentation
│
dashboard/src/
├── pages/plugins/                    # Plugin frontend pages
│   ├── cloud-ide.tsx                # CloudIDE full page
│   └── [plugin-name].tsx            # Other plugins...
│
├── components/layout/sidebar.tsx     # Fetches & displays plugins
└── lib/graphql-client.ts            # Plugin GraphQL query
```

## Plugin Lifecycle

1. **Registration** - Plugin registered at server startup
2. **Initialization** - `initialize()` called once
3. **Route Mounting** - API routes mounted to FastAPI
4. **Sidebar Display** - Plugin appears in sidebar (if enabled)
5. **User Access** - Clicking opens plugin's full page
6. **Shutdown** - `shutdown()` called when server stops

## Creating a Plugin

### Step 1: Create Plugin Folder

```bash
mkdir -p alphatrion/plugins/my_plugin
touch alphatrion/plugins/my_plugin/__init__.py
touch alphatrion/plugins/my_plugin/plugin.py
```

### Step 2: Implement Plugin Backend

```python
# alphatrion/plugins/my_plugin/plugin.py
from typing import Any
from fastapi import APIRouter
from alphatrion.plugins.base import Plugin, PluginMetadata

class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self._router = None

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-plugin",              # Unique ID
            name="My Plugin",             # Display name
            description="What it does",  # Short description
            icon="Package",               # Lucide icon name
            version="1.0.0",
            author="Your Name",
            route="/my-plugin",           # Frontend route
            sidebar_position=20,          # Lower = higher in sidebar
            enabled=True,
        )

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        # Create API router
        self._router = APIRouter(
            prefix="/api/plugins/my-plugin",
            tags=["my-plugin"]
        )

        # Define endpoints
        @self._router.get("/")
        async def index():
            return {"message": "Hello from MyPlugin"}

        @self._router.get("/data")
        async def get_data():
            return {"items": [...]}

    def get_api_router(self):
        """Return FastAPI router for mounting."""
        return self._router

    def shutdown(self) -> None:
        """Cleanup when plugin unloaded."""
        pass
```

```python
# alphatrion/plugins/my_plugin/__init__.py
from .plugin import MyPlugin

__all__ = ["MyPlugin"]
```

### Step 3: Register Plugin at Startup

```python
# In alphatrion/storage/runtime.py or app initialization
from alphatrion.plugins import register_plugin
from alphatrion.plugins.my_plugin import MyPlugin

def init():
    # ... existing initialization ...

    # Register plugins
    my_plugin = MyPlugin()
    my_plugin.initialize()
    register_plugin(my_plugin)
```

### Step 4: Mount Plugin Routes in FastAPI

```python
# In alphatrion/server/cmd/app.py
from alphatrion.plugins import get_registry

def create_app():
    app = FastAPI()

    # ... existing setup ...

    # Mount plugin routes
    registry = get_registry()
    for plugin in registry.list_enabled():
        router = plugin.get_api_router()
        if router:
            app.include_router(router)

    return app

app = create_app()
```

### Step 5: Create Frontend Page

```tsx
// dashboard/src/pages/plugins/my-plugin.tsx
import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';

export function MyPluginPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    // Fetch data from plugin API
    fetch('/api/plugins/my-plugin/data')
      .then(res => res.json())
      .then(setData);
  }, []);

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">My Plugin</h1>

      <Card>
        <CardHeader>
          <CardTitle>Plugin Data</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Your custom UI here */}
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Step 6: Add Route to React Router

```tsx
// dashboard/src/App.tsx or router config
import { MyPluginPage } from './pages/plugins/my-plugin';

// In routes array:
{
  path: '/my-plugin',
  element: <MyPluginPage />
}
```

### Step 7: Rebuild Frontend

```bash
cd dashboard
npm run build
```

## Sidebar Integration

The sidebar automatically fetches and displays plugins via GraphQL:

```tsx
// dashboard/src/components/layout/sidebar.tsx
import { useQuery } from '@tanstack/react-query';
import { graphqlQuery } from '../../lib/graphql-client';
import * as Icons from 'lucide-react';

const PLUGINS_QUERY = `
  query GetPlugins {
    plugins {
      id
      name
      description
      icon
      route
      enabled
    }
  }
`;

function Sidebar() {
  const { data: plugins } = useQuery({
    queryKey: ['plugins'],
    queryFn: async () => {
      const result = await graphqlQuery(PLUGINS_QUERY);
      return result.plugins;
    }
  });

  return (
    <nav>
      {/* Core nav items */}
      <NavItem icon={Home} to="/" label="Home" />
      <NavItem icon={FolderKanban} to="/projects" label="Projects" />

      {/* Plugin nav items */}
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
    </nav>
  );
}
```

## Example: CloudIDE Plugin

See `alphatrion/plugins/cloud_ide/` for a complete example:

1. **Backend** (`plugin.py`):
   - Defines metadata (name, icon, route)
   - Creates API router with endpoints
   - Returns router for mounting

2. **Frontend** (`dashboard/src/pages/plugins/cloud-ide.tsx`):
   - Full-page IDE interface
   - Code editor, file tree, terminal
   - Custom styling independent of main app

3. **Sidebar**:
   - Automatically shows "Cloud IDE" with Code icon
   - Clicking navigates to `/cloud-ide`

## Plugin API Reference

### PluginMetadata

```python
@dataclass
class PluginMetadata:
    id: str                    # Unique identifier (kebab-case)
    name: str                  # Display name for sidebar
    description: str           # Short description
    icon: str                  # Lucide-react icon name
    version: str               # Semantic version
    author: str | None = None  # Author name
    route: str = ""            # Frontend route (e.g., "/my-plugin")
    sidebar_position: int = 100  # Lower = higher in sidebar
    enabled: bool = True       # Whether plugin is active
```

### Plugin Methods

```python
class Plugin(ABC):
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize plugin (called once at startup)."""
        pass

    def get_api_router(self) -> APIRouter | None:
        """Return FastAPI router for API endpoints (optional)."""
        return None

    def get_frontend_bundle_path(self) -> str | None:
        """Return path to JS bundle (advanced usage)."""
        return None

    def shutdown(self) -> None:
        """Cleanup when plugin unloaded (optional)."""
        pass
```

## Best Practices

### 1. Plugin Isolation

Keep plugins completely isolated:

```
✅ GOOD                          ❌ BAD
alphatrion/plugins/my_plugin/    alphatrion/server/my_plugin_routes.py
├── __init__.py                  dashboard/src/components/my-plugin/
├── plugin.py                    (mixed with core code)
├── models.py
└── utils.py

dashboard/src/pages/plugins/
└── my-plugin.tsx
```

### 2. Error Handling

Plugins should never crash the main app:

```python
def initialize(self, config: dict | None = None) -> None:
    try:
        # Plugin initialization
        self._setup_database()
        self._create_router()
    except Exception as e:
        logger.error(f"Failed to initialize plugin: {e}")
        # Don't raise - allow app to continue
```

### 3. Configuration

Use metadata for plugin config:

```python
def initialize(self, config: dict | None = None) -> None:
    self._port = config.get("port", 8080) if config else 8080
    self._workspace = config.get("workspace", "/workspace") if config else "/workspace"
```

### 4. API Naming

Use consistent API patterns:

```python
# Good API structure
GET    /api/plugins/my-plugin/         # List resources
GET    /api/plugins/my-plugin/{id}     # Get resource
POST   /api/plugins/my-plugin/         # Create resource
PUT    /api/plugins/my-plugin/{id}     # Update resource
DELETE /api/plugins/my-plugin/{id}     # Delete resource
```

### 5. Frontend Independence

Make plugin pages self-contained:

```tsx
// Plugin page has its own styling and doesn't depend on core
export function MyPluginPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Completely custom UI */}
      <CustomHeader />
      <CustomSidebar />
      <CustomContent />
    </div>
  );
}
```

## Advanced Features

### Dynamic Plugin Loading

Future: Load plugins without restarting:

```python
# Coming soon
def reload_plugins():
    registry = get_registry()
    registry.discover_and_load('/path/to/plugins')
```

### Plugin Dependencies

Declare dependencies in metadata:

```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        id="advanced-plugin",
        dependencies=["cloud-ide"],  # Requires CloudIDE
        # ...
    )
```

### Inter-Plugin Communication

Use a message bus (future feature):

```python
# Plugin A
bus.publish('experiment.created', {'id': exp_id})

# Plugin B
bus.subscribe('experiment.created', on_experiment_created)
```

## Troubleshooting

### Plugin not showing in sidebar

1. Check `enabled=True` in metadata
2. Verify plugin is registered at startup
3. Check browser console for GraphQL errors
4. Verify frontend route is defined

### API endpoints not working

1. Check router is returned by `get_api_router()`
2. Verify router is mounted in `app.py`
3. Check endpoint prefix matches plugin ID
4. Test endpoint with curl: `curl http://localhost:8000/api/plugins/my-plugin/`

### Frontend page not loading

1. Verify route in `App.tsx` matches `metadata.route`
2. Check component is imported correctly
3. Rebuild frontend: `npm run build`
4. Check browser console for errors

## Migration Guide

### From Plugin System v1

If you built plugins with the old experiment-based system:

**Old (v1):**
- Plugins tied to experiments
- Showed as cards in experiment details
- Required experiment metadata

**New (v2):**
- Plugins are global navigation items
- Full-page interfaces in sidebar
- Independent of experiments

**Migration steps:**
1. Update `PluginMetadata` to include `route` and `sidebar_position`
2. Remove experiment-specific logic from plugin
3. Create dedicated frontend page in `dashboard/src/pages/plugins/`
4. Register plugin globally at startup (not per-experiment)

## Roadmap

- [ ] Hot-reload plugins without restart
- [ ] Plugin marketplace/discovery
- [ ] Plugin permissions & sandboxing
- [ ] Inter-plugin messaging
- [ ] Plugin configuration UI
- [ ] Plugin testing framework
- [ ] Plugin documentation generator

## Examples

See these example plugins:
- `cloud_ide/` - Browser-based code editor
- (More examples coming soon)

## Support

For questions or issues with the plugin system:
1. Check this documentation
2. Review example plugins
3. Open an issue on GitHub
