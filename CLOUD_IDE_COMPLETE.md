# Complete Cloud IDE Implementation

The Cloud IDE has been fully migrated from the forked project and integrated into the current codebase as a comprehensive plugin.

## Overview

The Cloud IDE provides a complete development environment with:
- **File Browser**: Navigate and manage files
- **Code Editor**: Monaco-based editor with syntax highlighting
- **Terminal**: Execute commands locally or in K8s pods
- **Chat Panel**: AI assistant integration (placeholder)
- **Dual Mode**: Local workspace or K8s sandbox support

## Architecture

### Component Structure

```
dashboard/src/
├── components/ide/
│   ├── repo/
│   │   ├── file-tree-simple.tsx    # File browser tree component
│   │   └── index.ts
│   ├── editor/
│   │   ├── monaco-code-editor.tsx  # Monaco code editor
│   │   └── index.ts
│   ├── terminal/
│   │   ├── terminal-panel-simple.tsx  # Terminal component
│   │   └── index.ts
│   └── chat/
│       ├── chat-simple.tsx         # Chat assistant component
│       └── index.ts
└── pages/plugins/
    ├── cloud-ide-full.tsx          # Main IDE page
    └── workspace.tsx                # Mode selector (local/K8s)
```

### Routes

- `/cloud-ide` - Main IDE interface (local mode by default)
- `/cloud-ide/:experimentId` - IDE with experiment context
- `/cloud-ide?pod=<pod-name>` - IDE connected to specific K8s pod

## Features

### 1. File Browser

**Capabilities:**
- Hierarchical file tree display
- Expandable/collapsible directories
- File selection highlighting
- Visual folder/file icons
- Breadcrumb navigation

**Implementation:**
- `FileTree` component renders recursive tree structure
- Supports both local filesystem and K8s pod file lists
- Click to expand folders, click files to open in editor

### 2. Code Editor

**Capabilities:**
- Syntax highlighting for 20+ languages
- Line numbers
- Auto-detection of language from file extension
- Modification tracking
- Keyboard shortcuts (Cmd+S to save)

**Supported Languages:**
- JavaScript, TypeScript, Python, Java, C/C++, Go, Rust
- Ruby, PHP, HTML, CSS, SCSS, JSON, YAML, XML
- Markdown, SQL, Shell scripts

**Implementation:**
- Uses Monaco Editor (@monaco-editor/react)
- Language auto-detection from file extension
- Real-time modification tracking
- Save indicator badge

### 3. Terminal Panel

**Capabilities:**
- Execute shell commands
- Command history in output
- Auto-scroll to latest output
- Enter key to execute
- Works with both local and K8s modes

**Implementation:**
- Simple terminal UI with command input
- Green-on-black terminal aesthetic
- Displays stdout and stderr
- Mode-aware (shows pod name in K8s mode)

### 4. Chat Assistant

**Capabilities:**
- Message history
- User/assistant message distinction
- Context-aware (knows current file, mode)
- Placeholder for AI integration

**Future Integration:**
- Connect to chat service API
- Code suggestions and explanations
- Debugging assistance
- Experiment insights

### 5. Panel Management

**Features:**
- Toggle file browser visibility
- Toggle terminal visibility
- Toggle chat panel visibility
- Resizable panels (fixed widths for now)
- Keyboard shortcuts

**Controls:**
- File Browser button (FolderTree icon)
- Terminal button (Terminal icon)
- Chat button (MessageSquare icon)
- Refresh button
- Save button

## Usage

### Opening the IDE

**Local Mode:**
```
Navigate to /cloud-ide in the dashboard
```

**K8s Pod Mode:**
```
Navigate to /cloud-ide?pod=cloud-ide-my-pod
```

**With Experiment Context:**
```
Navigate to /cloud-ide/experiment-uuid
```

### File Operations

**Open File:**
1. Click file in file browser
2. File loads in editor
3. Modification indicator appears if changed

**Save File:**
1. Edit file content
2. Press Cmd+S or click Save button
3. Confirmation on success

**Browse Files:**
1. Click folders to expand/collapse
2. Navigate tree structure
3. Selected file highlighted

### Terminal Usage

**Execute Command:**
1. Type command in terminal input
2. Press Enter
3. Output appears above

**Clear Terminal:**
Refresh the page (clear button coming soon)

### Panel Layout

**Default Layout:**
- File browser: Left (250px)
- Editor: Center (flexible)
- Terminal: Bottom (200px)
- Chat: Right (hidden by default)

**Toggle Panels:**
- Click icons in top bar to show/hide panels
- Editor always visible

## API Integration

### Local Workspace Mode

**Endpoints Used:**
- `GET /api/plugins/cloud-ide/files/tree` - Load file tree
- `GET /api/plugins/cloud-ide/files/content?path=...` - Read file
- `POST /api/plugins/cloud-ide/files/save` - Save file
- `POST /api/plugins/cloud-ide/terminal/execute` - Execute command

### K8s Sandbox Mode

**Endpoints Used:**
- `GET /api/plugins/cloud-ide/k8s/pods/{pod}/files/list` - List files
- `POST /api/plugins/cloud-ide/k8s/pods/{pod}/files/read` - Read file
- `POST /api/plugins/cloud-ide/k8s/pods/{pod}/files/write` - Write file
- `POST /api/plugins/cloud-ide/k8s/pods/{pod}/terminal/execute` - Execute command

## Dependencies

**Frontend:**
- `@monaco-editor/react` - Code editor
- `lucide-react` - Icons
- `react-router-dom` - Routing
- Existing UI components (Button, Input, Card, etc.)

**Backend:**
- FastAPI - Web framework
- Kubernetes Python client (optional, for K8s mode)
- psutil - Resource monitoring

## Migration Notes

### From Forked Project

**Components Migrated:**
- File browser (adapted to simpler structure)
- Monaco editor (kept original)
- Terminal panel (simplified)
- Chat panel (placeholder version)

**Components NOT Migrated:**
- Content evolution chart (experiment-specific, not general IDE)
- Lineage tree/history (experiment-specific)
- Comparison panel (experiment-specific)
- Repo browser hooks (rewritten for current structure)

**Data Model Changes:**
- Removed `trial` entity references
- Adapted to `experiment` entity
- No trial-specific features in general IDE

### Simplifications Made

1. **File Tree**: Removed complex RepoFileEntry type, used simpler FileNode
2. **Terminal**: Created simplified version without xterm.js
3. **Chat**: Created placeholder without full chat service integration
4. **Editor**: Kept Monaco as-is (already simple)

## Future Enhancements

### Planned Features

1. **Enhanced Terminal**
   - Interactive WebSocket terminal
   - xterm.js integration
   - Command history navigation
   - Clear/reset button

2. **AI Chat Integration**
   - Connect to backend chat service
   - Code completion suggestions
   - Debugging assistance
   - Natural language queries

3. **Advanced Editor Features**
   - Multi-file tabs
   - Split view
   - Find/replace
   - Go to definition
   - Code folding

4. **File Operations**
   - Create new files/folders
   - Delete files/folders
   - Rename files/folders
   - File upload/download
   - Drag-and-drop

5. **Panel Enhancements**
   - Resizable panels (draggable dividers)
   - Panel layouts (presets)
   - Full-screen mode
   - Remember user preferences

6. **Collaboration**
   - Real-time collaborative editing
   - User cursors/selections
   - Shared terminals
   - Integrated video/audio

7. **Git Integration**
   - View git status
   - Commit changes
   - Branch management
   - Diff viewer

8. **Debugging**
   - Breakpoint support
   - Variable inspection
   - Step through code
   - Call stack viewer

## Keyboard Shortcuts

- `Cmd/Ctrl + S` - Save file
- `Enter` (in terminal) - Execute command

**Coming Soon:**
- `Cmd/Ctrl + P` - Quick file search
- `Cmd/Ctrl + F` - Find in file
- `Cmd/Ctrl + /` - Toggle comment
- `Cmd/Ctrl + B` - Toggle file browser

## Troubleshooting

### Editor Not Loading

**Symptom**: Blank editor area

**Solution**:
1. Check browser console for errors
2. Ensure Monaco editor is loaded
3. Verify file content loaded successfully

### File Tree Not Showing

**Symptom**: Empty file browser

**Solutions**:
1. Check API endpoint `/api/plugins/cloud-ide/files/tree`
2. Verify workspace directory exists
3. Check permissions on workspace directory

### Terminal Commands Failing

**Symptom**: Error messages in terminal output

**Solutions**:
1. Verify command is valid for the environment
2. Check API endpoint is accessible
3. For K8s mode: verify pod is running and ready

### Save Not Working

**Symptom**: File doesn't save, or error on save

**Solutions**:
1. Check file permissions
2. Verify API endpoint responds
3. Check browser console for errors
4. Ensure file path is within workspace

## Summary

The Complete Cloud IDE is now fully integrated into the AlphaTrion project as the `cloud-ide` plugin. It provides a production-ready development environment with:

- ✅ File browsing and editing
- ✅ Code syntax highlighting for 20+ languages
- ✅ Terminal command execution
- ✅ Dual mode support (local/K8s)
- ✅ Clean, modern UI
- ✅ Keyboard shortcuts
- ✅ Modification tracking
- 🔄 Chat assistant (placeholder)

The IDE is accessible at `/cloud-ide` in the dashboard and automatically detects whether to use local or K8s mode based on URL parameters.
