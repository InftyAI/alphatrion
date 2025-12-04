import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect, createContext, useContext } from "react";
import { fetchProjects } from "../services/graphql";
import type { Project } from "../types";

// Components
import ExperimentsPage from "../components/Experiments/ExperimentsPage";
import ExperimentDetail from "../components/Experiments/ExperimentDetail";
import TrialsPage from "../components/Trials/TrialsPage";
import TrialDetail from "../components/Trials/TrialDetail";

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

        // Extract IDs from path like /experiments/:id or /trials/:id
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
            <div className="flex justify-center items-center h-screen bg-gray-100">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

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
            <div className="flex h-screen bg-gray-100">
                {/* Sidebar */}
                <div
                    className={`${sidebarOpen ? "w-64" : "w-16"} transition-all duration-300 bg-white shadow-lg flex-shrink-0`}
                >
                    <div className="flex flex-col h-full">
                        {/* Logo */}
                        <div className="flex items-center justify-between h-14 px-4 border-b">
                            {sidebarOpen && (
                                <span className="font-semibold text-gray-800">Alphatrion</span>
                            )}
                            <button
                                onClick={() => setSidebarOpen(!sidebarOpen)}
                                className="p-1 rounded hover:bg-gray-100 text-gray-500"
                            >
                                {sidebarOpen ? "<" : ">"}
                            </button>
                        </div>

                        {/* Project Selector */}
                        <div className="px-3 py-3 border-b">
                            {sidebarOpen ? (
                                <div>
                                    <label className="text-xs text-gray-500 uppercase tracking-wide">
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
                                        className="mt-1 block w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                                    className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 text-xs font-medium cursor-pointer"
                                    title={selectedProject?.name || "Select Project"}
                                >
                                    {selectedProject?.name?.charAt(0) || "P"}
                                </div>
                            )}
                        </div>

                        {/* Navigation */}
                        <nav className="flex-1 py-2">
                            {/* Experiments - always available */}
                            <Link
                                to={`/experiments?projectId=${selectedProjectId || ""}`}
                                className={`flex items-center h-10 px-4 text-sm transition-colors ${location.pathname.startsWith("/experiments")
                                    ? "text-blue-600 bg-blue-50 border-r-2 border-blue-600"
                                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                                    }`}
                            >
                                {sidebarOpen && "Experiments"}
                            </Link>

                            {/* Trials - needs experimentId */}
                            {selectedExperimentId ? (
                                <Link
                                    to={`/trials?experimentId=${selectedExperimentId}`}
                                    className={`flex items-center h-10 px-4 text-sm transition-colors ${location.pathname.startsWith("/trials")
                                        ? "text-blue-600 bg-blue-50 border-r-2 border-blue-600"
                                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                                        }`}
                                >
                                    {sidebarOpen && "Trials"}
                                </Link>
                            ) : (
                                <div
                                    className="flex items-center h-10 px-4 text-sm text-gray-300 cursor-not-allowed"
                                    title="Select an experiment first"
                                >
                                    {sidebarOpen && "Trials"}
                                </div>
                            )}

                            {/* Runs - needs trialId */}
                            {selectedTrialId ? (
                                <Link
                                    to={`/runs?trialId=${selectedTrialId}`}
                                    className={`flex items-center h-10 px-4 text-sm transition-colors ${location.pathname.startsWith("/runs")
                                        ? "text-blue-600 bg-blue-50 border-r-2 border-blue-600"
                                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                                        }`}
                                >
                                    {sidebarOpen && "Runs"}
                                </Link>
                            ) : (
                                <div
                                    className="flex items-center h-10 px-4 text-sm text-gray-300 cursor-not-allowed"
                                    title="Select a trial first"
                                >
                                    {sidebarOpen && "Runs"}
                                </div>
                            )}
                        </nav>

                        {/* Footer */}
                        <div className="border-t p-3">
                            {sidebarOpen && (
                                <div className="text-xs text-gray-400">Version 0.1.0</div>
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

// Placeholder for RunsPage - will create next
function RunsPage() {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-gray-900">Runs</h1>
            <p className="text-gray-600 mt-2">Coming soon...</p>
        </div>
    );
}

// Placeholder for RunDetail - will create next
function RunDetail() {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-gray-900">Run Detail</h1>
            <p className="text-gray-600 mt-2">Coming soon...</p>
        </div>
    );
}

export default App;