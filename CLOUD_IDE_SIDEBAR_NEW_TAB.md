# Cloud IDE Opens in New Tab from Sidebar

The Cloud IDE plugin now opens directly in a new browser tab when clicked from the sidebar, providing instant access to the full-screen IDE experience.

## Implementation

### Plugin Metadata Enhancement

Added `open_in_new_tab` field to plugin metadata to indicate plugins that should open externally.

**Backend (`alphatrion/plugins/base.py`):**
```python
@dataclass
class PluginMetadata:
    # ... existing fields ...
    open_in_new_tab: bool = False  # Whether to open in new browser tab
```

**Workspace Plugin (`alphatrion/plugins/workspace/plugin.py`):**
```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        id="cloud-ide",
        name="Cloud IDE",
        # ... other fields ...
        open_in_new_tab=True,  # Open in new browser tab
    )
```

### GraphQL Schema Update

Updated GraphQL types and resolvers to expose the new field.

**GraphQL Type (`alphatrion/server/graphql/types.py`):**
```python
@strawberry.type
class PluginInfo:
    # ... existing fields ...
    open_in_new_tab: bool
```

**GraphQL Resolver (`alphatrion/server/graphql/resolvers.py`):**
```python
PluginInfo(
    # ... existing fields ...
    open_in_new_tab=metadata.open_in_new_tab,
)
```

### Frontend Integration

**GraphQL Query (`dashboard/src/lib/graphql-client.ts`):**
```typescript
listPlugins: `
  query ListPlugins {
    plugins {
      id
      name
      # ... other fields ...
      openInNewTab
    }
  }
`
```

**TypeScript Type (`dashboard/src/types/index.ts`):**
```typescript
export interface PluginInfo {
  // ... existing fields ...
  openInNewTab: boolean;
}
```

**Sidebar Component (`dashboard/src/components/layout/sidebar.tsx`):**
```typescript
{plugins?.map((plugin) => {
  // For plugins that open in new tab
  if (plugin.openInNewTab) {
    const ideUrl = import.meta.env.DEV
      ? '/ide.html'
      : '/static/ide.html';

    return (
      <a
        href={ideUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="..."
      >
        <IconComponent />
        {plugin.name}
      </a>
    );
  }

  // Regular in-app navigation
  return <Link to={plugin.route}>...</Link>;
})}
```

## User Experience

### Before
1. Click "Cloud IDE" in sidebar
2. Navigate to workspace selector page
3. Choose local or K8s mode
4. Click "Open IDE" button
5. IDE opens in new tab

### After
1. Click "Cloud IDE" in sidebar
2. **IDE opens directly in new tab!** ✨

## Features

**Direct Access:**
- ✅ One-click access to IDE
- ✅ No intermediate page
- ✅ Faster workflow

**Smart URL Generation:**
- Development: Opens `/ide.html`
- Production: Opens `/static/ide.html`
- Respects Vite environment

**Standard Behavior:**
- Uses native `<a>` tag with `target="_blank"`
- Opens in new tab (browser preference)
- Includes `rel="noopener noreferrer"` for security

**Flexible Architecture:**
- Other plugins can use same mechanism
- Configure per-plugin basis
- Backward compatible (defaults to `false`)

## Technical Details

### Why `<a>` Instead of `window.open()`?

We use native `<a>` tags instead of programmatic `window.open()` because:

1. **Browser Control**: Users can right-click → "Open in new window" if preferred
2. **Middle-Click**: Users can middle-click to open in new tab
3. **Ctrl/Cmd+Click**: Standard modifier keys work
4. **No Popup Blockers**: Native links bypass popup blockers
5. **Accessibility**: Screen readers properly announce external links
6. **SEO Friendly**: Search engines can follow the links

### Security

The `rel="noopener noreferrer"` attribute prevents:
- **Tabnabbing attacks**: New page can't access `window.opener`
- **Referer leaking**: Referer header not sent to external page

### Styling

External links are styled consistently with other sidebar items:
- Same hover effects
- Same icon placement
- No visual distinction needed (behavior is expected)

## Configuration

### Making Any Plugin External

To make any plugin open in a new tab:

```python
class MyPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="my-plugin",
            name="My Plugin",
            route="/my-plugin",  # Can be any URL
            open_in_new_tab=True,  # Enable external opening
        )
```

The sidebar will automatically:
1. Detect `open_in_new_tab=True`
2. Use `<a>` tag instead of `<Link>`
3. Add `target="_blank"` and security attributes

### Custom URL Patterns

For plugins that need custom URLs (not just `/ide.html`), modify the sidebar component:

```typescript
if (plugin.openInNewTab) {
  let targetUrl: string;

  switch (plugin.id) {
    case 'cloud-ide':
      targetUrl = import.meta.env.DEV ? '/ide.html' : '/static/ide.html';
      break;
    case 'other-plugin':
      targetUrl = plugin.route; // Use route as-is
      break;
    default:
      targetUrl = plugin.route;
  }

  return <a href={targetUrl} target="_blank" ...>
}
```

## Backward Compatibility

**Existing Plugins:**
- All existing plugins have `open_in_new_tab=False` by default
- Continue to use in-app navigation with `<Link>`
- No changes required

**Plugin Registry:**
- New field is optional
- Gracefully handles plugins without the field
- TypeScript enforces type safety

## Alternative: Workspace Management Page

Users can still access the workspace management page at `/cloud-ide`:
- Manage K8s pods
- Deploy new sandboxes
- View pod status
- Choose workspace mode

This page is useful for:
- Managing multiple workspaces
- Configuring K8s pods
- Administrative tasks

The sidebar provides **quick access** to the default IDE, while the management page provides **full control**.

## Future Enhancements

### 1. Plugin URL Configuration

Allow plugins to specify exact URLs:

```python
PluginMetadata(
    route="/my-tool",
    external_url="https://external-tool.com",  # Optional external URL
    open_in_new_tab=True,
)
```

### 2. Window Features

Allow plugins to specify window dimensions:

```python
PluginMetadata(
    open_in_new_tab=True,
    window_features="width=1400,height=900,resizable=yes",
)
```

### 3. Context Passing

Pass experiment/project context to external pages:

```typescript
const ideUrl = `${baseUrl}?experimentId=${experimentId}`;
```

### 4. Multiple IDE Instances

Open multiple IDEs for different contexts:
- Right-click → "Open in new IDE"
- Per-experiment IDE instances
- Side-by-side comparison

### 5. Desktop App Integration

For Electron or Tauri desktop apps:
- Open IDE in separate window (not browser tab)
- Native window management
- Better multi-monitor support

## Testing

### Manual Testing Steps

1. **Start Backend:**
   ```bash
   alphatrion server
   ```

2. **Start Dashboard:**
   ```bash
   cd dashboard
   npm run dev
   ```

3. **Test Sidebar Click:**
   - Navigate to `http://localhost:5173`
   - Click "Cloud IDE" in sidebar
   - ✅ IDE should open in new tab
   - ✅ URL should be `/ide.html`

4. **Test in Production:**
   ```bash
   cd dashboard
   npm run build
   alphatrion dashboard --userid <user-id>
   ```
   - Click "Cloud IDE" in sidebar
   - ✅ IDE should open in new tab
   - ✅ URL should be `/static/ide.html`

5. **Test Right-Click:**
   - Right-click "Cloud IDE"
   - ✅ Context menu should show "Open in new tab/window"

6. **Test Middle-Click:**
   - Middle-click (or Ctrl+Click) "Cloud IDE"
   - ✅ Should open in new tab

## Troubleshooting

### Sidebar Click Opens in Same Tab

**Symptom**: IDE replaces dashboard instead of opening new tab

**Cause**: Plugin metadata not updated or GraphQL cache

**Solutions**:
1. Restart backend server
2. Clear browser cache
3. Hard refresh (Ctrl+Shift+R)
4. Check plugin metadata has `open_in_new_tab=True`

### Wrong URL in New Tab

**Symptom**: 404 or wrong page loads

**Cause**: Environment detection or build issue

**Solutions**:
1. Check if `ide.html` exists in appropriate location:
   - Dev: `/ide.html` in project root
   - Prod: `/static/ide.html` after build
2. Verify Vite build config includes both entry points
3. Check console for URL being used

### Popup Blocker Warning

**Symptom**: Browser shows "Popup blocked" notification

**Cause**: Using `window.open()` instead of `<a>` tag

**Solution**: Code uses `<a>` tag, so this shouldn't happen. If it does:
1. Verify sidebar implementation uses `<a>` not `window.open()`
2. Check browser popup settings

## Summary

The Cloud IDE now provides instant access from the sidebar:

✅ **One-click opening** - No intermediate steps
✅ **New tab behavior** - Keeps dashboard open
✅ **Smart URL detection** - Dev vs production
✅ **Secure** - Uses noopener/noreferrer
✅ **Accessible** - Native link behavior
✅ **Flexible** - Any plugin can use this pattern
✅ **Backward compatible** - Existing plugins unaffected

Click "Cloud IDE" in the sidebar → IDE opens instantly in a new tab!
