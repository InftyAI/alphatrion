import Editor, { type OnMount } from "@monaco-editor/react";
import { useRef, useCallback } from "react";

// Map language strings from mapLanguage() to Monaco language IDs
const LANGUAGE_MAP: Record<string, string> = {
    python: "python",
    javascript: "javascript",
    typescript: "typescript",
    jsx: "javascript",
    tsx: "typescript",
    java: "java",
    c: "c",
    cpp: "cpp",
    csharp: "csharp",
    go: "go",
    rust: "rust",
    ruby: "ruby",
    php: "php",
    swift: "swift",
    kotlin: "kotlin",
    scala: "scala",
    bash: "shell",
    shell: "shell",
    sql: "sql",
    html: "html",
    css: "css",
    scss: "scss",
    sass: "scss",
    less: "less",
    json: "json",
    yaml: "yaml",
    toml: "plaintext",
    xml: "xml",
    markdown: "markdown",
    r: "r",
    lua: "lua",
    perl: "perl",
    elixir: "plaintext",
    haskell: "plaintext",
    clojure: "clojure",
    vue: "html",
    svelte: "html",
    docker: "dockerfile",
    graphql: "graphql",
    text: "plaintext",
};

function mapToMonacoLanguage(language: string | null | undefined): string {
    if (!language) return "plaintext";
    return LANGUAGE_MAP[language.toLowerCase()] || "plaintext";
}

interface MonacoCodeEditorProps {
    content: string;
    language: string | null;
    filePath: string;
    onChange?: (value: string) => void;
    readOnly?: boolean;
}

export function MonacoCodeEditor({
    content,
    language,
    filePath,
    onChange,
    readOnly = false,
}: MonacoCodeEditorProps) {
    const editorRef = useRef<any>(null);

    const handleMount: OnMount = useCallback((editor) => {
        editorRef.current = editor;
    }, []);

    const handleChange = useCallback(
        (value: string | undefined) => {
            if (onChange && value !== undefined) {
                onChange(value);
            }
        },
        [onChange]
    );

    return (
        <Editor
            key={filePath}
            height="100%"
            language={mapToMonacoLanguage(language)}
            value={content}
            onChange={handleChange}
            onMount={handleMount}
            theme="vs"
            options={{
                readOnly,
                minimap: { enabled: false },
                fontSize: 12.8,
                lineHeight: 18,
                scrollBeyondLastLine: false,
                wordWrap: "off",
                automaticLayout: true,
                lineNumbers: "on",
                renderLineHighlight: "line",
                folding: true,
                glyphMargin: false,
                lineDecorationsWidth: 0,
                overviewRulerBorder: false,
                scrollbar: {
                    verticalScrollbarSize: 8,
                    horizontalScrollbarSize: 8,
                },
                padding: { top: 4, bottom: 4 },
            }}
        />
    );
}
