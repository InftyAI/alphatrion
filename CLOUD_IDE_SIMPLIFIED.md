# Cloud IDE - Simplified Version

Replaced the complex experiment-based IDE with a simple code editor + terminal interface, similar to the forked alphatrion project.

## Changes Made

### 1. Created New Simplified IDE Component

**File:** `src/pages/plugins/cloud-ide-simple.tsx`

Features:
- **File Explorer** (left sidebar): Browse files with folder/file icons
- **Code Editor** (center): Monaco editor with syntax highlighting
- **Terminal** (bottom): Interactive terminal for running commands
- **Header**: Shows current file name, Save and Run buttons

### 2. Removed Complex Features

What was removed:
- ❌ Project/Experiment selection dropdowns
- ❌ Evolution charts
- ❌ Lineage visualization
- ❌ Content snapshots
- ❌ Comparison tools
- ❌ Metrics tree

What remains:
- ✅ File tree navigation
- ✅ Code editor with syntax highlighting
- ✅ Terminal for command execution
- ✅ Save/Run buttons

### 3. Updated Route

**File:** `src/App.tsx`

```typescript
// Changed from:
<Route path="/plugins/cloud-ide" element={<CloudIDEFull />} />

// To:
<Route path="/plugins/cloud-ide" element={<CloudIDESimple />} />
```

## UI Layout

```
┌────────────────────────────────────────────────────────────┐
│ Cloud IDE          src/main.py ●         [Save]  [Run]    │
├──────────┬─────────────────────────────────────────────────┤
│ FILES    │ Code Editor                                     │
│          │                                                 │
│ □ src    │ # Main training script                         │
│   └ main │ import torch                                   │
│ □ tests  │ import torch.nn as nn                          │
│   └ test │ from model import Model                        │
│ README   │                                                 │
│ require  │ def train():                                   │
│          │     """Train the model"""                      │
│          │     model = Model()                            │
│          │                                                 │
├──────────┴─────────────────────────────────────────────────┤
│ TERMINAL                                                   │
│ $ Welcome to AlphaTrion Cloud IDE                          │
│ $ Type your commands here...                               │
│ $                                                           │
└────────────────────────────────────────────────────────────┘
```

## Features

### File Explorer
- Displays sample file tree with folders and files
- Click folders to expand/collapse
- Click files to open in editor
- Icons for folders and files

### Code Editor
- **Monaco Editor**: Same editor as VS Code
- **Syntax Highlighting**: Python, Markdown, etc.
- **Auto-save indication**: Shows ● when file has unsaved changes
- **Theme**: Dark theme (vs-dark)
- **Features**:
  - Line numbers
  - Auto-completion
  - Syntax validation
  - Keyboard shortcuts

### Terminal
- **Interactive shell**: Type commands and see output
- **Built-in commands**:
  - `ls` - List files
  - `python <file>` - Run Python script (simulated)
  - `clear` - Clear terminal
- **Green prompt**: `$` in green for better visibility
- **Command history**: Press up/down arrows (browser default)

### Header Controls
- **File name display**: Shows current open file
- **Unsaved indicator**: Shows ● when changes not saved
- **Save button**: Save current file (currently console.log)
- **Run button**: Execute current file (currently console.log)

## Sample Files Included

```
src/
  ├── main.py      # Main training script
  ├── model.py     # Model definition
  └── utils.py     # Utility functions

tests/
  └── test_main.py # Unit tests

README.md          # Project documentation
requirements.txt   # Python dependencies
```

## Sample File Content

**src/main.py:**
```python
# Main training script
import torch
import torch.nn as nn
from model import Model

def train():
    """Train the model"""
    model = Model()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(10):
        loss = model.train_step()
        print(f"Epoch {epoch}, Loss: {loss}")

    return model

if __name__ == "__main__":
    model = train()
    print("Training complete!")
```

## Terminal Commands

### Available Commands

1. **`ls`** - List files
   ```bash
   $ ls
   src/  tests/  README.md  requirements.txt
   ```

2. **`python <file>`** - Run Python script
   ```bash
   $ python src/main.py
   Running training...
   Epoch 0, Loss: 0.856
   Epoch 1, Loss: 0.742
   Epoch 2, Loss: 0.621
   Training complete!
   ```

3. **`clear`** - Clear terminal
   ```bash
   $ clear
   ```

4. **Any other command** - Shows error
   ```bash
   $ invalid-command
   bash: invalid-command: command not found
   ```

## Access URLs

### Development
```
http://localhost:5173/plugins/cloud-ide
```

### Production
```
http://localhost:8000/api/plugins/cloud-ide/ide
```

## Technical Details

### Technologies Used
- **React**: UI framework
- **Monaco Editor**: Code editor (from VS Code)
- **Lucide React**: Icons
- **Flexbox**: Layout (no complex resizing library)
- **Tailwind CSS**: Styling

### State Management
```typescript
const [selectedFile, setSelectedFile] = useState<string | null>('src/main.py');
const [fileContents, setFileContents] = useState<Record<string, string>>(sampleFiles);
const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
```

### File Operations
Currently stubbed out:
```typescript
const handleSave = () => {
  console.log('Saving file:', selectedFile);
  // TODO: Implement save to backend
};

const handleRun = () => {
  console.log('Running file:', selectedFile);
  // TODO: Implement run in terminal
};
```

## Next Steps - Backend Integration

### 1. Connect to Real File System
Replace sample files with real filesystem access:
```typescript
// Fetch file tree from backend
const { data: fileTree } = useFetch('/api/files/tree');

// Fetch file content
const { data: content } = useFetch(`/api/files/content?path=${path}`);

// Save file
await fetch('/api/files/save', {
  method: 'POST',
  body: JSON.stringify({ path, content }),
});
```

### 2. Connect Terminal to Backend
Use WebSocket or Server-Sent Events for real terminal:
```typescript
const ws = new WebSocket('ws://localhost:8000/terminal');

ws.onmessage = (event) => {
  setOutput(prev => [...prev, event.data]);
};

// Send command
ws.send(input);
```

### 3. Add File Operations
- Create new file
- Delete file
- Rename file
- Create folder

### 4. Add More Editor Features
- Multiple tabs (open multiple files)
- Split editor view
- Search and replace
- Git integration
- Debugging

## Comparison: Before vs After

### Before (CloudIDEFull)
- Complex experiment-based workflow
- Required selecting project and experiment first
- Included evolution charts, lineage, metrics
- 870+ lines of code
- Multiple dependencies

### After (CloudIDESimple)
- Simple code editor workflow
- Works immediately, no setup needed
- Just file explorer, editor, and terminal
- 350 lines of code
- Minimal dependencies

## Benefits

1. **Simpler UX**: No need to select projects/experiments
2. **Faster load**: No complex data fetching
3. **Easier to understand**: Traditional IDE layout
4. **More maintainable**: Less code, fewer dependencies
5. **Familiar**: Works like VS Code or other IDEs

## Testing

1. **Start dev server:**
   ```bash
   npm run dev
   ```

2. **Navigate to:**
   ```
   http://localhost:5173/plugins/cloud-ide
   ```

3. **Test features:**
   - Click files in file explorer
   - Edit code in editor
   - See unsaved changes indicator (●)
   - Click Save button
   - Type commands in terminal
   - See terminal output

## Summary

Created a simplified Cloud IDE that:
- ✅ Shows code editor and terminal directly
- ✅ No experiment selection required
- ✅ Traditional IDE layout (file explorer + editor + terminal)
- ✅ Sample files and commands included
- ✅ Ready for backend integration
- ✅ Matches the forked alphatrion project approach
