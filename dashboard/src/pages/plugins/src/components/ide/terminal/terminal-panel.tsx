import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { syncFilesToPod } from "../../services/graphql";
import "@xterm/xterm/css/xterm.css";

type ConnectionState = "connecting" | "connected" | "disconnected" | "error";

interface TerminalPanelProps {
    podName: string;
    fileModifications?: Map<string, string>;
    onConnectionChange?: (connected: boolean) => void;
}

const MAX_RETRIES = 10;
const RETRY_BASE_MS = 2000;

export default function TerminalPanel({
    podName,
    fileModifications,
    onConnectionChange,
}: TerminalPanelProps) {
    const termRef = useRef<HTMLDivElement>(null);
    const [connectionState, setConnectionState] =
        useState<ConnectionState>("connecting");
    const [retryCount, setRetryCount] = useState(0);

    // Refs to survive across renders without causing re-effects
    const wsRef = useRef<WebSocket | null>(null);
    const terminalRef = useRef<Terminal | null>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    const onConnectionChangeRef = useRef(onConnectionChange);
    onConnectionChangeRef.current = onConnectionChange;
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const mountedRef = useRef(true);
    // Track which files have been synced to avoid re-syncing on reconnect
    const syncedFilesRef = useRef<string | null>(null);

    // Create terminal once on mount
    useEffect(() => {
        mountedRef.current = true;

        const term = new Terminal({
            cursorBlink: true,
            convertEol: true,
            scrollback: 5000,
            fontSize: 13,
            fontFamily: "Menlo, Monaco, 'Courier New', monospace",
            theme: {
                background: "#1a1b26",
                foreground: "#a9b1d6",
                cursor: "#c0caf5",
                selectionBackground: "#33467c",
                black: "#32344a",
                red: "#f7768e",
                green: "#9ece6a",
                yellow: "#e0af68",
                blue: "#7aa2f7",
                magenta: "#ad8ee6",
                cyan: "#449dab",
                white: "#787c99",
                brightBlack: "#444b6a",
                brightRed: "#ff7a93",
                brightGreen: "#b9f27c",
                brightYellow: "#ff9e64",
                brightBlue: "#7da6ff",
                brightMagenta: "#bb9af7",
                brightCyan: "#0db9d7",
                brightWhite: "#acb0d0",
            },
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        terminalRef.current = term;
        fitAddonRef.current = fitAddon;

        if (termRef.current) {
            termRef.current.innerHTML = "";
            term.open(termRef.current);
            fitAddon.fit();
        }

        return () => {
            mountedRef.current = false;
            if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
            if (wsRef.current) wsRef.current.close();
            term.dispose();
            terminalRef.current = null;
            fitAddonRef.current = null;
            wsRef.current = null;
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Sync files to pod when modifications change
    useEffect(() => {
        if (!fileModifications || fileModifications.size === 0) return;

        // Build a fingerprint to detect actual changes
        const fingerprint = JSON.stringify(
            Array.from(fileModifications.entries()).sort()
        );
        if (syncedFilesRef.current === fingerprint) return;

        const term = terminalRef.current;
        let cancelled = false;

        (async () => {
            try {
                const files: Record<string, string> = {};
                for (const [path, content] of fileModifications) {
                    files[path] = content;
                }

                if (term) {
                    term.write(
                        `\r\n\x1b[33mSyncing ${fileModifications.size} modified file(s) to pod...\x1b[0m\r\n`
                    );
                }

                const result = await syncFilesToPod(podName, files);

                if (cancelled) return;
                syncedFilesRef.current = fingerprint;

                if (term) {
                    if (result.errors.length > 0) {
                        term.write(
                            `\x1b[31mSynced ${result.written}/${result.total} files (${result.errors.length} errors)\x1b[0m\r\n`
                        );
                    } else {
                        const paths = result.paths || {};
                        for (const [rel, abs] of Object.entries(paths)) {
                            term.write(`\x1b[32m  ${rel} -> ${abs}\x1b[0m\r\n`);
                        }
                        term.write(
                            `\x1b[32mSynced ${result.written} file(s) to pod.\x1b[0m\r\n`
                        );
                    }
                }
            } catch (err) {
                if (cancelled) return;
                if (term) {
                    term.write(
                        `\x1b[31mFailed to sync files: ${err}\x1b[0m\r\n`
                    );
                }
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [podName, fileModifications]);

    // Connect WebSocket (separate from terminal creation)
    useEffect(() => {
        const term = terminalRef.current;
        if (!term) return;

        // Build WebSocket URL
        const apiBase =
            import.meta.env.VITE_API_BASE_URL ||
            (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
        const wsBase = apiBase
            .replace(/^https:\/\//, "wss://")
            .replace(/^http:\/\//, "ws://");
        const wsUrl = wsBase
            ? `${wsBase}/api/terminal/${encodeURIComponent(podName)}`
            : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/terminal/${encodeURIComponent(podName)}`;

        let retries = 0;
        let currentWs: WebSocket | null = null;
        let cancelled = false;
        let observer: ResizeObserver | null = null;

        function attemptConnect() {
            if (cancelled || !mountedRef.current) return;
            if (currentWs) currentWs.close();

            setConnectionState("connecting");
            console.log(`[Terminal] Connecting to: ${wsUrl} (attempt ${retries + 1})`);

            const ws = new WebSocket(wsUrl);
            currentWs = ws;
            wsRef.current = ws;

            ws.onopen = () => {
                if (cancelled) return;
                // Don't reset retries or set "connected" here — wait for
                // server confirmation after K8s exec stream is established
                setConnectionState("connecting");
                // Send initial resize
                const t = terminalRef.current;
                if (t) {
                    ws.send(`resize:${t.cols},${t.rows}`);
                }
            };

            ws.onmessage = (event) => {
                if (cancelled) return;
                const data: string = event.data;
                // Server sends this after K8s exec stream is established
                if (data.includes("Connected to pod shell.")) {
                    retries = 0;
                    setRetryCount(0);
                    setConnectionState("connected");
                    onConnectionChangeRef.current?.(true);
                }
                terminalRef.current?.write(data);
            };

            ws.onclose = () => {
                if (cancelled) return;
                setConnectionState("disconnected");
                onConnectionChangeRef.current?.(false);
                // Auto-retry if we haven't exceeded max
                if (retries < MAX_RETRIES) {
                    const delay = RETRY_BASE_MS * Math.min(retries + 1, 5);
                    retries++;
                    setRetryCount(retries);
                    // Only show verbose reconnect message after several failures
                    if (retries > 3) {
                        terminalRef.current?.write(
                            `\x1b[90m[Retrying... (${retries}/${MAX_RETRIES})]\x1b[0m\r\n`
                        );
                    }
                    retryTimerRef.current = setTimeout(attemptConnect, delay);
                } else {
                    terminalRef.current?.write(
                        "\r\n\x1b[31m[Connection failed after max retries. Click Reconnect to try again.]\x1b[0m\r\n"
                    );
                    setConnectionState("error");
                }
            };

            ws.onerror = () => {
                // onerror is always followed by onclose, so let onclose handle retry
            };
        }

        attemptConnect();

        // Terminal input -> WebSocket
        term.onData((data: string) => {
            if (currentWs?.readyState === WebSocket.OPEN) {
                currentWs.send(data);
            }
        });

        // Resize handling
        observer = new ResizeObserver(() => {
            fitAddonRef.current?.fit();
            if (currentWs?.readyState === WebSocket.OPEN) {
                const { cols, rows } = term;
                currentWs.send(`resize:${cols},${rows}`);
            }
        });
        if (termRef.current) {
            observer.observe(termRef.current);
        }

        return () => {
            cancelled = true;
            if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
            if (currentWs) currentWs.close();
            if (observer) observer.disconnect();
            wsRef.current = null;
        };
    }, [podName]);

    const handleReconnect = () => {
        const term = terminalRef.current;
        if (!term) return;
        setRetryCount(0);
        term.write("\r\n\x1b[90m[Reconnecting...]\x1b[0m\r\n");
        if (wsRef.current) wsRef.current.close();
    };

    const statusColor: Record<ConnectionState, string> = {
        connecting: "bg-yellow-400",
        connected: "bg-green-400",
        disconnected: "bg-gray-400",
        error: "bg-red-400",
    };

    const statusText = () => {
        switch (connectionState) {
            case "connecting":
                return retryCount > 0
                    ? `Retrying (${retryCount}/${MAX_RETRIES})...`
                    : "Connecting...";
            case "connected":
                return "Connected";
            case "disconnected":
                return retryCount > 0
                    ? `Reconnecting (${retryCount}/${MAX_RETRIES})...`
                    : "Disconnected";
            case "error":
                return "Connection failed";
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Status bar */}
            <div className="flex items-center justify-between px-3 py-1.5 bg-[#1a1b26] border-b border-gray-700 rounded-t-lg">
                <div className="flex items-center gap-2">
                    <span
                        className={`h-2 w-2 rounded-full ${statusColor[connectionState]} ${connectionState === "connecting" ? "animate-pulse" : ""}`}
                    />
                    <span className="text-xs text-gray-400 font-mono">
                        {podName}
                    </span>
                    <span className="text-xs text-gray-500">
                        {statusText()}
                    </span>
                </div>
                {connectionState === "error" && (
                    <button
                        type="button"
                        onClick={handleReconnect}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                        Reconnect
                    </button>
                )}
            </div>
            {/* Terminal container */}
            <div
                ref={termRef}
                className="flex-1 min-h-0 bg-[#1a1b26] rounded-b-lg"
                style={{ padding: "4px" }}
            />
        </div>
    );
}
