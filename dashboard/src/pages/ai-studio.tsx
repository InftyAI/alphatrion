import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
    Play,
    Trash2,
    RefreshCw,
    Code2,
    Terminal as TerminalIcon,
    FolderOpen,
} from "lucide-react";
import { MonacoCodeEditor } from "../components/ai-studio/editor";
import { TerminalPanel } from "../components/ai-studio/terminal";
import { FileTree } from "../components/ai-studio/repo";

type TabType = "editor" | "terminal";
type PodStatus = "pending" | "deploying" | "ready" | "failed" | "not_found";

interface PodInfo {
    name: string;
    status: PodStatus;
    image: string;
    error?: string;
}

export default function AIStudioPage() {
    const [activeTab, setActiveTab] = useState<TabType>("editor");
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState<string>("");
    const [fileLanguage, setFileLanguage] = useState<string | null>("python");
    const [pods, setPods] = useState<PodInfo[]>([]);
    const [selectedPod, setSelectedPod] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Mock file tree data (replace with actual API call)
    const mockFileTree = {
        name: "root",
        path: "/",
        isDir: true,
        children: [
            {
                name: "src",
                path: "/src",
                isDir: true,
                children: [
                    { name: "main.py", path: "/src/main.py", isDir: false, children: [] },
                    { name: "utils.py", path: "/src/utils.py", isDir: false, children: [] },
                ],
            },
            { name: "README.md", path: "/README.md", isDir: false, children: [] },
        ],
    };

    const handleFileSelect = async (filePath: string) => {
        setSelectedFile(filePath);
        // TODO: Fetch file content from API
        setFileContent(`# Sample content for ${filePath}\n\nprint("Hello from AI Studio!")`);

        // Infer language from file extension
        const ext = filePath.split('.').pop()?.toLowerCase();
        const langMap: Record<string, string> = {
            py: 'python',
            js: 'javascript',
            ts: 'typescript',
            tsx: 'typescript',
            jsx: 'javascript',
            go: 'go',
            rs: 'rust',
            java: 'java',
            cpp: 'cpp',
            c: 'c',
        };
        setFileLanguage(langMap[ext || ''] || 'plaintext');
    };

    const handleFileChange = (content: string) => {
        setFileContent(content);
        // TODO: Track file modifications
    };

    const deployPod = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/ai-studio/pod/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    experiment_name: 'test-experiment',
                    sandbox_image: 'python:3.12-slim',
                }),
            });
            const data = await response.json();

            setPods([
                ...pods,
                {
                    name: data.pod_name,
                    status: data.status,
                    image: 'python:3.12-slim',
                    error: data.error,
                },
            ]);
        } catch (error) {
            console.error('Failed to deploy pod:', error);
        } finally {
            setLoading(false);
        }
    };

    const refreshPodStatus = async (podName: string) => {
        try {
            const response = await fetch(`/api/ai-studio/pod/${podName}/status`);
            const data = await response.json();

            setPods(pods.map(p =>
                p.name === podName
                    ? { ...p, status: data.status, error: data.error }
                    : p
            ));
        } catch (error) {
            console.error('Failed to refresh pod status:', error);
        }
    };

    const deletePod = async (podName: string) => {
        if (!confirm(`Delete pod ${podName}?`)) return;

        try {
            await fetch(`/api/ai-studio/pod/${podName}`, { method: 'DELETE' });
            setPods(pods.filter(p => p.name !== podName));
            if (selectedPod === podName) {
                setSelectedPod(null);
            }
        } catch (error) {
            console.error('Failed to delete pod:', error);
        }
    };

    const getStatusColor = (status: PodStatus) => {
        const colors: Record<PodStatus, string> = {
            pending: 'bg-yellow-500',
            deploying: 'bg-yellow-500',
            ready: 'bg-green-500',
            failed: 'bg-red-500',
            not_found: 'bg-gray-500',
        };
        return colors[status];
    };

    return (
        <div className="flex flex-col h-screen bg-background">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Code2 className="h-6 w-6" />
                        AI Studio
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        Cloud-based code editor with sandbox execution
                    </p>
                </div>
                <Button onClick={deployPod} disabled={loading} className="gap-2">
                    <Play className="h-4 w-4" />
                    Deploy Sandbox
                </Button>
            </div>

            {/* Main Content */}
            <div className="flex flex-1 min-h-0">
                {/* Left Sidebar - File Tree */}
                <div className="w-64 border-r flex flex-col">
                    <div className="px-4 py-3 border-b">
                        <h3 className="font-semibold text-sm flex items-center gap-2">
                            <FolderOpen className="h-4 w-4" />
                            Files
                        </h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2">
                        <FileTree
                            root={mockFileTree}
                            onSelectFile={handleFileSelect}
                            selectedPath={selectedFile}
                        />
                    </div>
                </div>

                {/* Center - Editor/Terminal */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Tabs */}
                    <div className="flex items-center gap-2 px-4 py-2 border-b">
                        <Button
                            variant={activeTab === "editor" ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setActiveTab("editor")}
                            className="gap-2"
                        >
                            <Code2 className="h-4 w-4" />
                            Editor
                        </Button>
                        <Button
                            variant={activeTab === "terminal" ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setActiveTab("terminal")}
                            className="gap-2"
                            disabled={!selectedPod}
                        >
                            <TerminalIcon className="h-4 w-4" />
                            Terminal
                            {!selectedPod && (
                                <Badge variant="secondary" className="ml-1">Select Pod</Badge>
                            )}
                        </Button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-h-0 p-4">
                        {activeTab === "editor" ? (
                            selectedFile ? (
                                <Card className="h-full">
                                    <CardHeader>
                                        <CardTitle className="text-sm font-mono">
                                            {selectedFile}
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="h-[calc(100%-4rem)]">
                                        <MonacoCodeEditor
                                            content={fileContent}
                                            language={fileLanguage}
                                            filePath={selectedFile}
                                            onChange={handleFileChange}
                                            readOnly={false}
                                        />
                                    </CardContent>
                                </Card>
                            ) : (
                                <Card className="h-full flex items-center justify-center">
                                    <CardContent className="text-center text-muted-foreground">
                                        <Code2 className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                        <p>Select a file to start editing</p>
                                    </CardContent>
                                </Card>
                            )
                        ) : selectedPod ? (
                            <Card className="h-full">
                                <CardContent className="p-0 h-full">
                                    <TerminalPanel podName={selectedPod} />
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="h-full flex items-center justify-center">
                                <CardContent className="text-center text-muted-foreground">
                                    <TerminalIcon className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                    <p>Select a pod to open terminal</p>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>

                {/* Right Sidebar - Sandbox Pods */}
                <div className="w-80 border-l flex flex-col">
                    <div className="px-4 py-3 border-b">
                        <h3 className="font-semibold text-sm">Sandbox Pods</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {pods.length === 0 ? (
                            <div className="text-center text-sm text-muted-foreground py-8">
                                No active sandbox pods.
                                <br />
                                Deploy one to get started.
                            </div>
                        ) : (
                            pods.map((pod) => (
                                <Card
                                    key={pod.name}
                                    className={`cursor-pointer transition-colors ${
                                        selectedPod === pod.name
                                            ? 'ring-2 ring-blue-500'
                                            : 'hover:bg-accent/50'
                                    }`}
                                    onClick={() => setSelectedPod(pod.name)}
                                >
                                    <CardContent className="p-3">
                                        <div className="flex items-start justify-between gap-2 mb-2">
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate">
                                                    {pod.name}
                                                </p>
                                                <p className="text-xs text-muted-foreground truncate">
                                                    {pod.image}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <span
                                                    className={`h-2 w-2 rounded-full ${getStatusColor(pod.status)}`}
                                                />
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-1">
                                            <Badge variant="secondary" className="text-xs">
                                                {pod.status}
                                            </Badge>

                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    refreshPodStatus(pod.name);
                                                }}
                                                className="h-6 w-6 p-0"
                                                title="Refresh status"
                                            >
                                                <RefreshCw className="h-3 w-3" />
                                            </Button>

                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    deletePod(pod.name);
                                                }}
                                                className="h-6 w-6 p-0 text-red-500 hover:text-red-600"
                                                title="Delete pod"
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </Button>
                                        </div>

                                        {pod.error && (
                                            <p className="text-xs text-red-500 mt-2">
                                                {pod.error}
                                            </p>
                                        )}
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
