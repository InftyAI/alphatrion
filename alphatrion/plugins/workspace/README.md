# Workspace Plugin

AI development environment for Alphatrion, inspired by Lightning.ai AI Studio.

## Features

### 📁 File Management
- **File Explorer** - Browse workspace files in a tree view
- **File Editor** - Edit files with syntax highlighting
- **Create/Delete/Rename** - Full file and directory operations
- **Auto-save Detection** - Track unsaved changes

### 💻 Integrated Terminal
- **Command Execution** - Run shell commands directly
- **Output Capture** - View stdout and stderr
- **Working Directory** - Execute commands in context
- **Command History** - Track executed commands

### 🔧 Environment Management
- **Python Info** - View Python version and path
- **Package List** - See installed pip packages
- **Environment Variables** - Access environment configuration

### 📊 Resource Monitoring
- **CPU Usage** - Real-time CPU percentage
- **Memory Usage** - RAM usage and percentage
- **Disk Usage** - Storage space monitoring
- **GPU Detection** - Show available GPUs (if nvidia-smi available)

## API Endpoints

### File System

```bash
# Get file tree
GET /api/plugins/workspace/files/tree?path=

# Read file content
GET /api/plugins/workspace/files/content?path=file.py

# Save file
POST /api/plugins/workspace/files/save
{
  "path": "file.py",
  "content": "print('hello')"
}

# Create file or directory
POST /api/plugins/workspace/files/create
{
  "path": "new_file.py",
  "type": "file",
  "content": "# New file"
}

# Delete file or directory
POST /api/plugins/workspace/files/delete?path=file.py

# Rename file or directory
POST /api/plugins/workspace/files/rename
{
  "old_path": "old.py",
  "new_path": "new.py"
}
```

### Terminal

```bash
# Execute command
POST /api/plugins/workspace/terminal/execute
{
  "command": "python script.py",
  "cwd": "path/to/directory"  # optional
}

# Response:
{
  "stdout": "output here",
  "stderr": "errors here",
  "returncode": 0
}
```

### Environment

```bash
# Get environment info
GET /api/plugins/workspace/environment/info

# Response:
{
  "python_version": "3.11.0",
  "python_path": "/usr/bin/python3",
  "platform": "Linux-5.15.0",
  "architecture": "x86_64"
}

# List installed packages
GET /api/plugins/workspace/environment/packages

# Response:
{
  "packages": [
    {"name": "numpy", "version": "1.24.0"},
    ...
  ]
}
```

### Resources

```bash
# Get resource status
GET /api/plugins/workspace/resources/status

# Response:
{
  "cpu_percent": 45.2,
  "memory_total": 16777216000,
  "memory_used": 8388608000,
  "memory_percent": 50.0,
  "disk_total": 1000000000000,
  "disk_used": 500000000000,
  "disk_percent": 50.0,
  "gpus": [
    {"info": "Tesla V100, 32GB, 2GB used"}
  ]
}
```

## Configuration

Configure the workspace root directory when initializing the plugin:

```python
from alphatrion.plugins.workspace import WorkspacePlugin

workspace = WorkspacePlugin()
workspace.initialize({
    "workspace_root": "/path/to/workspace"
})
```

Default workspace location: `~/alphatrion-workspace`

## Security

### Path Safety
- All file operations are restricted to workspace root directory
- Path traversal attempts (e.g., `../../etc/passwd`) are blocked
- Returns 403 Forbidden for paths outside workspace

### Command Execution
- Terminal commands run with user privileges
- 30-second timeout to prevent hanging
- Sandboxing recommended for production use

### File Access
- Hidden files (starting with `.`) excluded from tree view
- Common directories (`__pycache__`, `node_modules`) excluded
- Binary files cannot be read as text

## Frontend Components

### Layout

```
+------------------+-------------------------+
|                  |   Toolbar               |
|   File           +-------------------------+
|   Explorer       |                         |
|                  |   Editor / Terminal     |
|   [Tree]         |   (Tabs)                |
|                  |                         |
|                  |                         |
+------------------+                         |
|   Resources      |                         |
|   - CPU          |                         |
|   - Memory       |                         |
|   - Disk         +-------------------------+
+------------------+
```

### File Tree
- Click folders to expand/collapse
- Click files to open in editor
- Shows file/folder icons
- Sorts directories first, then files alphabetically

### Editor
- Monospace font for code
- Detects modifications (shows "Modified" badge)
- Save button enabled when file is modified
- Full-screen text area

### Terminal
- Command input with Enter key support
- Output display with stdout/stderr
- Command history in output
- Execute button for running commands

### Resource Monitoring
- Updates every 5 seconds
- Compact sidebar display
- Color-coded badges
- GPU count indicator

## Usage Examples

### Opening and Editing a File

1. Navigate to workspace page (`/workspace`)
2. Click on a file in the file tree
3. File content loads in editor
4. Make changes
5. Click "Save" button (or Ctrl+S)

### Running a Python Script

1. Switch to "Terminal" tab
2. Type command: `python script.py`
3. Press Enter or click Run button
4. View output in terminal window

### Creating a New File

```python
import requests

# Create a new Python file
response = requests.post(
    'http://localhost:8000/api/plugins/workspace/files/create',
    json={
        'path': 'my_script.py',
        'type': 'file',
        'content': '#!/usr/bin/env python3\nprint("Hello, World!")'
    }
)
```

### Monitoring Resources

Resources are automatically monitored and displayed in the sidebar. The plugin polls the resource endpoint every 5 seconds to update:
- CPU usage percentage
- Memory usage and percentage
- Disk usage and percentage
- GPU count (if available)

## Dependencies

### Backend
- `fastapi` - API framework
- `psutil` - Resource monitoring
- `pathlib` - File operations
- Standard library (`subprocess`, `os`, etc.)

### Frontend
- React
- Lucide icons
- Tailwind CSS
- shadcn/ui components

### Optional
- `nvidia-smi` - For GPU detection (if available)
- `pip` - For package listing

## Limitations

### Current Version
- Single workspace per user (no multi-workspace support)
- No Jupyter notebook integration (planned)
- Basic text editor (no Monaco/CodeMirror yet)
- Terminal is command-by-command, not interactive shell
- No collaboration features
- No Git integration (planned)

### Security Considerations
- Commands run with server user privileges
- No sandboxing by default
- File permissions match server process
- Consider using containers for isolation in production

## Future Enhancements

### Planned Features
- [ ] Monaco editor integration for better code editing
- [ ] Syntax highlighting by file type
- [ ] Jupyter notebook support
- [ ] Interactive terminal (WebSocket-based)
- [ ] Git integration (status, diff, commit)
- [ ] Multi-workspace support
- [ ] Collaborative editing
- [ ] Code completion and IntelliSense
- [ ] Debugger integration
- [ ] Docker container support
- [ ] Environment variable management
- [ ] Extension system for custom tools

### Performance Optimizations
- [ ] Lazy loading for large file trees
- [ ] File content streaming for large files
- [ ] Debounced auto-save
- [ ] Caching for file metadata
- [ ] WebSocket for real-time updates

## Troubleshooting

### File tree not loading
- Check workspace_root configuration
- Verify directory permissions
- Check backend logs for errors

### Terminal commands failing
- Verify command exists in PATH
- Check command timeout (default 30s)
- Review stderr output for errors

### Resource monitoring not working
- Ensure `psutil` is installed: `pip install psutil`
- For GPU monitoring, ensure `nvidia-smi` is in PATH

### Cannot save files
- Check file write permissions
- Verify disk space available
- Check for path traversal errors (403)

## Development

### Running the Plugin

```bash
# Backend server
cd alphatrion
python -m alphatrion.server.cmd.main server

# The workspace will be accessible at:
# http://localhost:8000/workspace
```

### Testing APIs

```bash
# Test file tree
curl http://localhost:8000/api/plugins/workspace/files/tree

# Test terminal
curl -X POST http://localhost:8000/api/plugins/workspace/terminal/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "echo Hello"}'

# Test resources
curl http://localhost:8000/api/plugins/workspace/resources/status
```

## Contributing

To extend the workspace plugin:

1. Add new endpoints in `plugin.py`
2. Update API models (Pydantic classes)
3. Add corresponding frontend functions
4. Update this README with new features
5. Add tests for new functionality

## License

Same as Alphatrion project license.
