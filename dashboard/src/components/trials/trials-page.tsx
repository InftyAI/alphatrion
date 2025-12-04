import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTrials } from "../../hooks/use-trials";
import { format } from "date-fns";
import type { Trial } from "../../types";

type TabType = "overview" | "list";

const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
        COMPLETED: "bg-green-100 text-green-800",
        RUNNING: "bg-blue-100 text-blue-800",
        PENDING: "bg-yellow-100 text-yellow-800",
        FAILED: "bg-red-100 text-red-800",
        CANCELLED: "bg-gray-100 text-gray-800",
        UNKNOWN: "bg-gray-100 text-gray-500",
    };

    return (
        <span className={`px-2 py-1 text-xs rounded-full ${colors[status] || colors.UNKNOWN}`}>
            {status}
        </span>
    );
};

export default function TrialsPage() {
    const [searchParams] = useSearchParams();
    const experimentId = searchParams.get("experimentId");
    const [activeTab, setActiveTab] = useState<TabType>("overview");

    const { data: trials, isLoading, error } = useTrials(experimentId);

    if (!experimentId) {
        return (
            <div className="p-6">
                <div className="bg-yellow-50 p-4 rounded">
                    <p className="text-yellow-800">
                        No experiment selected. Please select an experiment from the{" "}
                        <Link to="/experiments" className="text-blue-600 underline">
                            Experiments page
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
                    <p className="text-red-600">Error loading trials: {error.message}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Trials</h1>
                <p className="text-gray-600">
                    Experiment ID: <span className="font-mono text-sm">{experimentId}</span>
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
                        List ({trials?.length ?? 0})
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === "overview" ? (
                <OverviewTable trials={trials ?? []} />
            ) : (
                <ListTable trials={trials ?? []} />
            )}
        </div>
    );
}

// Overview Table Component
function OverviewTable({ trials }: { trials: Trial[] }) {
    const totalTrials = trials.length;
    const completedTrials = trials.filter((t) => t.status === "COMPLETED").length;
    const runningTrials = trials.filter((t) => t.status === "RUNNING").length;
    const failedTrials = trials.filter((t) => t.status === "FAILED").length;
    const avgDuration = trials.length > 0
        ? trials.reduce((sum, t) => sum + t.duration, 0) / trials.length
        : 0;

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
                            Total Trials
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">{totalTrials}</td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Completed
                        </td>
                        <td className="px-6 py-4 text-sm text-green-600">{completedTrials}</td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Running
                        </td>
                        <td className="px-6 py-4 text-sm text-blue-600">{runningTrials}</td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Failed
                        </td>
                        <td className="px-6 py-4 text-sm text-red-600">{failedTrials}</td>
                    </tr>
                    <tr>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            Average Duration
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">{avgDuration.toFixed(2)}s</td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

// List Table Component
function ListTable({ trials }: { trials: Trial[] }) {
    if (trials.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
                No trials found for this experiment.
            </div>
        );
    }

    return (
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
                            Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Duration
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Created
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {trials.map((trial) => (
                        <tr key={trial.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                                <Link
                                    to={`/trials/${trial.id}`}
                                    className="text-sm font-mono text-blue-600 hover:text-blue-900"
                                >
                                    {trial.id}
                                </Link>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="text-sm text-gray-900">{trial.name}</span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <StatusBadge status={trial.status} />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="text-sm text-gray-900">{trial.duration.toFixed(2)}s</span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="text-sm text-gray-500">
                                    {format(new Date(trial.createdAt), "MMM d, yyyy")}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}