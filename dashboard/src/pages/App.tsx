import { Routes, Route, Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { fetchProjects } from "../services/graphql";
import type { Project } from "../types";

// Components
import ExperimentsPage from "../components/Experiments/ExperimentsPage";
import ExperimentDetail from "../components/Experiments/ExperimentDetail";
import TrialDetail from "../components/Trials/TrialDetail";

// Projects Dashboard
function ProjectsDashboard() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    useEffect(() => {
        const isFirstVisit = sessionStorage.getItem("hasVisited") !== "true";

        fetchProjects()
            .then((data) => {
                setProjects(data);
                setLoading(false);
                // Auto-navigate to first project only on first visit
                if (isFirstVisit && data.length > 0) {
                    sessionStorage.setItem("hasVisited", "true");
                    navigate(`/experiments?projectId=${data[0].id}`);
                }
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, [navigate]);

    if (loading) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="bg-red-50 p-4 rounded">
                    <p className="text-red-600">Error: {error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Projects</h1>
            <p className="text-gray-600 mb-6">
                {projects.length} projects available.
            </p>

            <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Description
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {projects.map((project) => (
                            <tr key={project.id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <Link
                                        to={`/experiments?projectId=${project.id}`}
                                        className="text-sm font-mono text-blue-600 hover:text-blue-900"
                                    >
                                        {project.id}
                                    </Link>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className="text-sm text-gray-900">
                                        {project.name || "Unnamed"}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-gray-500">
                                        {project.description || "-"}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function App() {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(true);

    const navigation = [
        { name: "Projects", href: "/" },
    ];

    return (
        <div className="flex h-screen bg-gray-100">
            {/* Sidebar */}
            <div
                className={`${sidebarOpen ? "w-64" : "w-16"} transition-all duration-300 bg-white shadow-lg`}
            >
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center justify-between h-16 px-4 border-b">
                        {sidebarOpen && (
                            <h1 className="text-lg font-bold text-gray-800">Alphatrion</h1>
                        )}
                        <button
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            className="p-2 rounded hover:bg-gray-100"
                        >
                            {sidebarOpen ? "<" : ">"}
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4">
                        {navigation.map((item) => {
                            const isActive =
                                location.pathname === item.href ||
                                (item.href !== "/" && location.pathname.startsWith(item.href));
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={`flex items-center gap-3 px-3 py-2 mb-2 rounded-lg transition-colors ${isActive
                                        ? "bg-blue-50 text-blue-700"
                                        : "hover:bg-gray-100 text-gray-700"
                                        }`}
                                >
                                    {sidebarOpen && (
                                        <span className="font-medium">{item.name}</span>
                                    )}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Footer */}
                    <div className="p-4 border-t">
                        {sidebarOpen && (
                            <div className="text-sm text-gray-500">
                                <p>Version 0.1.0</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto">
                <Routes>
                    <Route path="/" element={<ProjectsDashboard />} />
                    <Route path="/experiments" element={<ExperimentsPage />} />
                    <Route path="/experiments/:id" element={<ExperimentDetail />} />
                    <Route path="/trials/:id" element={<TrialDetail />} />
                </Routes>
            </div>
        </div>
    );
}

export default App;