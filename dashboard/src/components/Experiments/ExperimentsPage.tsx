import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useExperiments } from "../../hooks/useExperiments";
import { useTrials } from "../../hooks/useTrials";
import { format } from "date-fns";
import type { Experiment } from "../../types";

type TabType = "overview" | "list";

export default function ExperimentsPage() {
    const [searchParams] = useSearchParams();
    const projectId = searchParams.get("projectId");
    const [activeTab, setActiveTab] = useState<TabType>("overview");

    const { data: experiments, isLoading, error } = useExperiments(projectId);

    if (!projectId) {
        return (
            <div className="p-6">
                <div className="bg-yellow-50 p-4 rounded">
                    <p className="text-yellow-800">
                        No project selected. Please select a project from the{" "}
                        <Link to="/" className="text-blue-600 underline">
                            Projects page
                        </Link>
                        .
                    </p>
                </div>
            </div>
        );
    }

    if (isLoading) {
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
                    <p className="text-red-600">Error loading experiments: {error.message}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Experiments</h1>
                <p className="text-gray-600">
                    Project ID: <span className="font-mono text-sm">{projectId.slice(0, 8)}...</span>
                </p>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="flex gap-4">
                    <button
                        onClick={() => setActiveTab("overview")}
                        className={`py-2 px-4 border-b-2 font-medium text-sm ${activeTab === "overview"
                            ? "border-blue-600 text-blue-600"
                            : "border-transparent text-gray-500 hover:text-gray-700"
                            }`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab("list")}
                        className={`py-2 px-4 border-b-2 font-medium text-sm ${activeTab === "list"
                            ? "border-blue-600 text-blue-600"
                            : "border-transparent text-gray-500 hover:text-gray-700"
                            }`}
                    >
                        List ({experiments?.length ?? 0})
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === "overview" ? (
                <OverviewTable experiments={experiments ?? []} />
            ) : (
                <ListTable experiments={experiments ?? []} />
            )}
        </div>
    );
}

// Overview Table Component
function OverviewTable({ experiments }: { experiments: Experiment[] }) {
    const totalExperiments = experiments.length;

    // For MVP, we show basic stats. In future, can add more aggregations.
    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Metric
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Value
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Total Experiments
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">{totalExperiments}</td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Latest Experiment
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                            {experiments.length > 0
                                ? experiments[0].name || "Unnamed"
                                : "-"}
                        </td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Oldest Experiment
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                            {experiments.length > 0
                                ? experiments[experiments.length - 1].name || "Unnamed"
                                : "-"}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

// List Table Component
function ListTable({ experiments }: { experiments: Experiment[] }) {
    if (experiments.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
                No experiments found for this project.
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Name
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Description
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Created
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            ID
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {experiments.map((exp) => (
                        <tr key={exp.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                                <Link
                                    to={`/experiments/${exp.id}`}
                                    className="text-sm font-medium text-blue-600 hover:text-blue-900"
                                >
                                    {exp.name || "Unnamed Experiment"}
                                </Link>
                            </td>
                            <td className="px-6 py-4">
                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                    {exp.description || "-"}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-500">
                                    {format(new Date(exp.createdAt), "MMM d, yyyy")}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-500 font-mono">
                                    {exp.id.slice(0, 8)}...
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}