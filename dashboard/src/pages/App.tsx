import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect, createContext, useContext } from "react";
import { fetchProjects } from "../services/graphql";
import type { Project } from "../types";
import { ChevronLeft, ChevronRight, FlaskConical } from "lucide-react";
import packageJson from "../../package.json";

// Components
import ExperimentsPage from "../components/experiments/experiments-page";
import ExperimentDetail from "../components/experiments/experiment-detail";
import TrialsPage from "../components/trials/trials-page";
import TrialDetail from "../components/trials/trial-detail";
import RunsPage from "../components/runs/runs-page";
import RunDetail from "../components/runs/run-detail";

// Context for selected IDs
interface SelectionContextType {
    projectId: string | null;
    experimentId: string | null;
    trialId: string | null;
    setProjectId: (id: string | null) => void;
    setExperimentId: (id: string | null) => void;
    setTrialId: (id: string | null) => void;
}

const SelectionContext = createContext<SelectionContextType | null>(null);

export function useSelection() {
    const ctx = useContext(SelectionContext);
    if (!ctx) throw new Error("useSelection must be used within App");
    return ctx;
}

function App() {
    const location = useLocation();
    const navigate = useNavigate();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    // Projects
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // Selected experiment and trial
    const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);
    const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null);

    // Load projects on mount
    useEffect(() => {
        fetchProjects()
            .then((data) => {
                setProjects(data);
                if (data.length > 0) {
                    setSelectedProjectId(data[0].id);
                }
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to load projects:", err);
                setLoading(false);
            });
    }, []);

    // Navigate to experiments when project changes
    useEffect(() => {
        if (selectedProjectId && location.pathname === "/") {
            navigate(`/experiments?projectId=${selectedProjectId}`);
        }
    }, [selectedProjectId]);

    // Update selected IDs from URL
    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const projectId = params.get("projectId");
        const experimentId = params.get("experimentId");
        const trialId = params.get("trialId");

        if (projectId) setSelectedProjectId(projectId);
        if (experimentId) setSelectedExperimentId(experimentId);
        if (trialId) setSelectedTrialId(trialId);

        const pathParts = location.pathname.split("/");
        if (pathParts[1] === "experiments" && pathParts[2]) {
            setSelectedExperimentId(pathParts[2]);
        }
        if (pathParts[1] === "trials" && pathParts[2]) {
            setSelectedTrialId(pathParts[2]);
        }
    }, [location]);

    const selectedProject = projects.find((p) => p.id === selectedProjectId) || null;

    if (loading) {
        return (
            <div className="flex justify-center items-center h-screen">
                <div className="relative">
                    <div className="w-16 h-16 border-4 border-indigo-200 rounded-full animate-spin border-t-indigo-600"></div>
                    <img src="/static/logo.png" alt="Loading" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6" />
                </div>
            </div>
        );
    }

    // Sidebar now only has Experiments — Trials and Runs removed
    const navItems = [
        {
            key: "experiments",
            label: "Experiments",
            icon: FlaskConical,
            path: `/experiments?projectId=${selectedProjectId || ""}`,
            active: location.pathname.startsWith("/experiments"),
            enabled: true,
        }
    ];

    return (
        <SelectionContext.Provider
            value={{
                projectId: selectedProjectId,
                experimentId: selectedExperimentId,
                trialId: selectedTrialId,
                setProjectId: setSelectedProjectId,
                setExperimentId: setSelectedExperimentId,
                setTrialId: setSelectedTrialId,
            }}
        >
            <div className="flex h-screen">
                {/* Sidebar */}
                <div
                    className={`${sidebarOpen ? "w-64" : "w-19"}
                    transition-all duration-300 flex-shrink-0
                    bg-white/70 backdrop-blur-xl
                    border-r border-gray-200/50
                    shadow-[1px_0_30px_-15px_rgba(0,0,0,0.1)]`}
                >
                    <div className="flex flex-col h-full">
                        {/* Logo */}
                        <div className="flex items-center justify-between h-16 px-3 border-b border-gray-200/50">
                            <div className="flex items-center gap-3">
                                <img src="/static/logo.png" alt="AlphaTrion" className="w-9 h-9 rounded-xl flex-shrink-0" />
                                {sidebarOpen && (
                                    <span className="font-bold text-lg bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                                        AlphaTrion
                                    </span>
                                )}
                            </div>
                            {/*
                            <button
                                onClick={() => setSidebarOpen(!sidebarOpen)}
                                className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
                            >
                                {sidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
                            </button>
                                */}
                        </div>

                        {/* Project Selector */}
                        <div className="px-3 py-4 border-b border-gray-200/50">
                            {sidebarOpen ? (
                                <div>
                                    <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                                        Project
                                    </label>
                                    <select
                                        value={selectedProjectId || ""}
                                        onChange={(e) => {
                                            const id = e.target.value;
                                            setSelectedProjectId(id);
                                            setSelectedExperimentId(null);
                                            setSelectedTrialId(null);
                                            navigate(`/experiments?projectId=${id}`);
                                        }}
                                        className="mt-2 block w-full px-3 py-2 text-sm bg-gray-50/80 border border-gray-200 rounded-lg
                                        focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400
                                        transition-all cursor-pointer hover:bg-gray-100/80"
                                    >
                                        {projects.map((p) => (
                                            <option key={p.id} value={p.id}>
                                                {p.name || p.id.slice(0, 8)}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            ) : (
                                <div
                                    className="w-10 h-10 bg-gradient-to-br from-gray-100 to-gray-50 rounded-lg flex items-center justify-center
                                    text-indigo-600 text-sm font-semibold cursor-pointer border border-gray-200
                                    hover:shadow-md transition-all mx-auto"
                                    title={selectedProject?.name || "Select Project"}
                                >
                                    {selectedProject?.name?.charAt(0).toUpperCase() || "P"}
                                </div>
                            )}
                        </div>

                        {/* Navigation */}
                        <nav className="flex-1 py-4 px-3 space-y-1">
                            {navItems.map((item) => {
                                const Icon = item.icon;

                                return (
                                    <Link
                                        key={item.key}
                                        to={item.path}
                                        className={`flex items-center gap-3 h-11 px-3 rounded-lg transition-all duration-200
                                            ${!sidebarOpen && "justify-center"}
                                            ${item.active
                                                ? "bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/25"
                                                : "text-gray-600 hover:bg-gray-100/80 hover:text-gray-900"
                                            }`}
                                    >
                                        <Icon size={20} />
                                        {sidebarOpen && <span className="font-medium text-sm">{item.label}</span>}
                                    </Link>
                                );
                            })}
                        </nav>

                        {/* Footer */}
                        <div className="border-t border-gray-200/50 p-4">
                            {sidebarOpen ? (
                                <span className="text-xs text-gray-400">v{packageJson.version}</span>
                            ) : (
                                <span className="text-xs text-gray-400 block text-center">
                                    v{packageJson.version.split('.')[0]}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1 overflow-auto">
                    <Routes>
                        <Route path="/" element={<div />} />
                        <Route path="/experiments" element={<ExperimentsPage />} />
                        <Route path="/experiments/:id" element={<ExperimentDetail />} />

                        {/* Still keep routes — only removed from sidebar */}
                        <Route path="/trials" element={<TrialsPage />} />
                        <Route path="/trials/:id" element={<TrialDetail />} />
                        <Route path="/runs" element={<RunsPage />} />
                        <Route path="/runs/:id" element={<RunDetail />} />
                    </Routes>
                </div>
            </div>
        </SelectionContext.Provider>
    );
}

export default App;
