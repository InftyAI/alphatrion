import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { File, AlertCircle } from "lucide-react";
import type { RepoFileContent } from "../../types";

interface FileViewerProps {
    content: RepoFileContent | null;
    isLoading: boolean;
    error?: string | null;
}

// Map GraphQL language to prism language
function mapLanguage(language: string | undefined | null): string {
    if (!language) return "text";

    const languageMap: Record<string, string> = {
        "python": "python",
        "javascript": "javascript",
        "typescript": "typescript",
        "jsx": "jsx",
        "tsx": "tsx",
        "java": "java",
        "c": "c",
        "cpp": "cpp",
        "csharp": "csharp",
        "go": "go",
        "rust": "rust",
        "ruby": "ruby",
        "php": "php",
        "swift": "swift",
        "kotlin": "kotlin",
        "scala": "scala",
        "bash": "bash",
        "shell": "bash",
        "sql": "sql",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "sass": "sass",
        "less": "less",
        "json": "json",
        "yaml": "yaml",
        "toml": "toml",
        "xml": "xml",
        "markdown": "markdown",
        "restructuredtext": "text",
        "r": "r",
        "lua": "lua",
        "perl": "perl",
        "elixir": "elixir",
        "erlang": "erlang",
        "haskell": "haskell",
        "clojure": "clojure",
        "vue": "vue",
        "svelte": "svelte",
        "dockerfile": "docker",
        "hcl": "hcl",
        "protobuf": "protobuf",
        "graphql": "graphql",
    };

    return languageMap[language.toLowerCase()] || "text";
}

export default function FileViewer({ content, isLoading, error }: FileViewerProps) {
    // Loading state
    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
        );
    }

    // Error state
    if (error || content?.error) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                <AlertCircle className="h-8 w-8 text-destructive" />
                <p className="text-sm">{error || content?.error}</p>
            </div>
        );
    }

    // No file selected
    if (!content) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                <File className="h-12 w-12" />
                <p className="text-sm">Select a file to view its contents</p>
            </div>
        );
    }

    // File content
    const language = mapLanguage(content.language);

    return (
        <SyntaxHighlighter
            language={language}
            style={oneLight}
            showLineNumbers
            wrapLines
            customStyle={{
                margin: 0,
                fontSize: "0.8rem",
            }}
            lineNumberStyle={{
                minWidth: "3em",
                paddingRight: "1em",
                textAlign: "right",
                color: "#999",
                borderRight: "1px solid #eee",
                marginRight: "1em",
            }}
        >
            {content.content || ""}
        </SyntaxHighlighter>
    );
}
