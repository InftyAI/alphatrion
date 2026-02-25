import { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { File, Folder, FolderOpen, Terminal as TerminalIcon, Play, Save } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { useTeamContext } from '../../context/team-context';
import { useProjects } from '../../hooks/use-projects';
import { useExperiments } from '../../hooks/use-experiments';
import type { Project, Experiment } from '../../types';

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
}

// Sample file tree
const sampleFileTree: FileNode[] = [
  {
    name: 'src',
    type: 'folder',
    path: 'src',
    children: [
      { name: 'main.py', type: 'file', path: 'src/main.py' },
      { name: 'model.py', type: 'file', path: 'src/model.py' },
      { name: 'utils.py', type: 'file', path: 'src/utils.py' },
    ],
  },
  {
    name: 'tests',
    type: 'folder',
    path: 'tests',
    children: [
      { name: 'test_main.py', type: 'file', path: 'tests/test_main.py' },
    ],
  },
  { name: 'README.md', type: 'file', path: 'README.md' },
  { name: 'requirements.txt', type: 'file', path: 'requirements.txt' },
];

// Sample file contents
const sampleFiles: Record<string, string> = {
  'src/main.py': `# Main training script
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
`,
  'src/model.py': `# Model definition
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.fc1(x)
        x = self.fc2(x)
        return x

    def train_step(self):
        # Training logic here
        return 0.5
`,
  'README.md': `# AlphaTrion Project

This is a sample ML training project.

## Setup

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Usage

\`\`\`bash
python src/main.py
\`\`\`
`,
  'requirements.txt': `torch==2.0.0
numpy==1.24.0
pandas==2.0.0
`,
};

function FileTreeItem({ node, selectedFile, onSelectFile, level = 0 }: {
  node: FileNode;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  level?: number;
}) {
  const [isOpen, setIsOpen] = useState(true);

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsOpen(!isOpen);
    } else {
      onSelectFile(node.path);
    }
  };

  const isSelected = selectedFile === node.path;

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1 cursor-pointer hover:bg-accent/50 ${
          isSelected ? 'bg-accent text-accent-foreground' : ''
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        {node.type === 'folder' ? (
          isOpen ? (
            <FolderOpen className="h-4 w-4 text-blue-500" />
          ) : (
            <Folder className="h-4 w-4 text-blue-500" />
          )
        ) : (
          <File className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="text-sm">{node.name}</span>
      </div>
      {node.type === 'folder' && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.path}
              node={child}
              selectedFile={selectedFile}
              onSelectFile={onSelectFile}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SimpleTerminal() {
  const [output, setOutput] = useState<string[]>([
    '$ Welcome to AlphaTrion Cloud IDE',
    '$ Type your commands here...',
    '',
  ]);
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add command to output
    const newOutput = [...output, `$ ${input}`];

    // Simulate command execution
    if (input === 'ls') {
      newOutput.push('src/  tests/  README.md  requirements.txt');
    } else if (input.startsWith('python')) {
      newOutput.push('Running training...');
      newOutput.push('Epoch 0, Loss: 0.856');
      newOutput.push('Epoch 1, Loss: 0.742');
      newOutput.push('Epoch 2, Loss: 0.621');
      newOutput.push('Training complete!');
    } else if (input === 'clear') {
      setOutput([]);
      setInput('');
      return;
    } else {
      newOutput.push(`bash: ${input}: command not found`);
    }

    newOutput.push('');
    setOutput(newOutput);
    setInput('');
  };

  return (
    <div className="h-full flex flex-col bg-[#1e1e1e] text-gray-100 font-mono">
      {/* Terminal output */}
      <div className="flex-1 overflow-auto p-3 text-sm">
        {output.map((line, i) => (
          <div key={i} className={line.startsWith('$') ? 'text-green-400' : ''}>
            {line}
          </div>
        ))}
      </div>

      {/* Terminal input */}
      <form onSubmit={handleSubmit} className="border-t border-gray-700 p-2 flex items-center gap-2">
        <span className="text-green-400">$</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 bg-transparent outline-none text-sm"
          placeholder="Enter command..."
          autoFocus
        />
      </form>
    </div>
  );
}

export default function CloudIDESimple() {
  // Project and experiment selection
  const { selectedTeamId } = useTeamContext();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);

  // Fetch projects and experiments
  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const { data: experiments = [], isLoading: experimentsLoading } = useExperiments(
    selectedProjectId ?? "",
    { enabled: !!selectedProjectId }
  );

  // Auto-select first project
  useEffect(() => {
    if (!selectedProjectId && projects.length > 0) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  // File editor state
  const [selectedFile, setSelectedFile] = useState<string | null>('src/main.py');
  const [fileContents, setFileContents] = useState<Record<string, string>>(sampleFiles);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const currentContent = selectedFile ? fileContents[selectedFile] || '' : '';

  const handleEditorChange = (value: string | undefined) => {
    if (selectedFile && value !== undefined) {
      setFileContents({
        ...fileContents,
        [selectedFile]: value,
      });
      setHasUnsavedChanges(true);
    }
  };

  const handleSave = () => {
    // TODO: Implement save to backend
    console.log('Saving file:', selectedFile);
    setHasUnsavedChanges(false);
  };

  const handleRun = () => {
    // TODO: Implement run in terminal
    console.log('Running file:', selectedFile);
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold">Cloud IDE</h1>

          {/* Project Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Project:</span>
            <Select
              value={selectedProjectId ?? ""}
              onValueChange={(value) => {
                setSelectedProjectId(value);
                setSelectedExperimentId(null);
              }}
              disabled={projectsLoading || projects.length === 0}
            >
              <SelectTrigger className="w-[180px] h-8">
                <SelectValue placeholder="Select project..." />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project: Project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name || project.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Experiment Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Experiment:</span>
            <Select
              value={selectedExperimentId ?? ""}
              onValueChange={setSelectedExperimentId}
              disabled={!selectedProjectId || experimentsLoading || experiments.length === 0}
            >
              <SelectTrigger className="w-[180px] h-8">
                <SelectValue placeholder="Select experiment..." />
              </SelectTrigger>
              <SelectContent>
                {experiments
                  .filter((exp: Experiment) => exp.projectId === selectedProjectId)
                  .map((exp: Experiment) => (
                    <SelectItem key={exp.id} value={exp.id}>
                      {exp.name || exp.id}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          {/* Current file */}
          {selectedFile && (
            <span className="text-sm text-muted-foreground ml-4">
              {selectedFile}
              {hasUnsavedChanges && <span className="ml-1">●</span>}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleSave}
            disabled={!hasUnsavedChanges}
          >
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
          <Button
            size="sm"
            onClick={handleRun}
            disabled={!selectedFile}
          >
            <Play className="h-4 w-4 mr-1" />
            Run
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden flex">
        {/* File explorer */}
        <div className="w-[15%] min-w-[200px] border-r">
          <Card className="h-full rounded-none border-0 border-r">
            <div className="p-2 border-b bg-muted/50">
              <h2 className="text-xs font-semibold text-muted-foreground">FILES</h2>
            </div>
            <div className="overflow-auto" style={{ height: 'calc(100% - 33px)' }}>
              {sampleFileTree.map((node) => (
                <FileTreeItem
                  key={node.path}
                  node={node}
                  selectedFile={selectedFile}
                  onSelectFile={setSelectedFile}
                />
              ))}
            </div>
          </Card>
        </div>

        {/* Editor and terminal */}
        <div className="flex-1 flex flex-col">
          {/* Code editor */}
          <div className="flex-1 overflow-hidden" style={{ height: '70%' }}>
            {selectedFile ? (
              <Editor
                height="100%"
                defaultLanguage={selectedFile.endsWith('.py') ? 'python' : 'markdown'}
                value={currentContent}
                onChange={handleEditorChange}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <File className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Select a file to edit</p>
                </div>
              </div>
            )}
          </div>

          {/* Terminal */}
          <div className="h-[30%] min-h-[200px] border-t">
            <Card className="h-full rounded-none border-0">
              <div className="p-2 border-b bg-muted/50 flex items-center gap-2">
                <TerminalIcon className="h-4 w-4" />
                <h2 className="text-xs font-semibold">TERMINAL</h2>
              </div>
              <div style={{ height: 'calc(100% - 33px)' }}>
                <SimpleTerminal />
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
