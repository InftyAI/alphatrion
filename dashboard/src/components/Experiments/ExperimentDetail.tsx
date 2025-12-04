import { Link, useParams } from "react-router-dom";
import { useExperimentDetail } from "../../hooks/useExperimentDetail";
import { format } from "date-fns";
import type { Trial } from "../../types";
import { useSelection } from "../../pages/App";
import { useEffect, useState } from "react";

// Status badge component
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

export default function ExperimentDetail() {
    const { id } = useParams<{ id: string }>();
    const { experiment, trials, isLoading, error } = useExperimentDetail(id ?? null);
    const { setExperimentId } = useSelection();

    const [activeTab, setActiveTab] = useState<"overview" | "trials">("overview");

    useEffect(() => {
        if (experiment) setExperimentId(experiment.id);
    }, [experiment, setExperimentId]);

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
                    <p className="text-red-600">Error: {error.message}</p>
                </div>
            </div>
        );
    }

    if (!experiment) {
        return (
            <div className="p-6">
                <div className="bg-yellow-50 p-4 rounded">
                    <p className="text-yellow-800">Experiment not found.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Breadcrumb */}
            <div className="mb-4 text-sm text-gray-500">
                <Link to="/" className="hover:text-blue-600">Projects</Link>
                <span className="mx-2">/</span>
                <Link
                    to={`/experiments?projectId=${experiment.projectId}`}
                    className="hover:text-blue-600"
                >
                    Experiments
                </Link>
                <span className="mx-2">/</span>
                <span className="text-gray-900">{experiment.name || "Detail"}</span>
            </div>

            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">
                    {experiment.name || "Unnamed Experiment"}
                </h1>
                <p className="text-gray-600 mt-1">
                    {experiment.description || "No description"}
                </p>
            </div>

            {/* Tabs */}
            <div className="inline-flex p-1 bg-gray-100/80 rounded-xl mb-6">
                <button
                    onClick={() => setActiveTab("overview")}
                    className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === "overview"
                        ? "bg-white text-gray-900 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                        }`}
                >
                    Overview
                </button>
                <button
                    onClick={() => setActiveTab("trials")}
                    className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === "trials"
                        ? "bg-white text-gray-900 shadow-sm"
                        : "text-gray-500 hover:text-gray-700"
                        }`}
                >
                    Trials
                    <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">
                        {trials.length}
                    </span>
                </button>
            </div>

            {/* Tab content */}
            {activeTab === "overview" ? (
                <OverviewTab experiment={experiment} />
            ) : (
                <TrialsTab trials={trials} />
            )}
        </div>
    );
}

/* -------------------- OVERVIEW TAB -------------------- */

function OverviewTab({ experiment }: { experiment: any }) {
    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Experiment Info</h2>

            <div className="grid grid-cols-2 gap-4">
                <InfoItem label="ID" value={experiment.id} mono />
                <InfoItem label="Project ID" value={experiment.projectId} mono />
                <InfoItem
                    label="Created"
                    value={format(new Date(experiment.createdAt), "MMM d, yyyy HH:mm")}
                />
                <InfoItem
                    label="Updated"
                    value={format(new Date(experiment.updatedAt), "MMM d, yyyy HH:mm")}
                />
            </div>

            {experiment.meta && Object.keys(experiment.meta).length > 0 && (
                <div className="mt-4">
                    <p className="text-sm text-gray-500 mb-2">Metadata</p>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                        {JSON.stringify(experiment.meta, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}

function InfoItem({ label, value, mono = false }: any) {
    return (
        <div>
            <p className="text-sm text-gray-500">{label}</p>
            <p className={`text-sm ${mono ? "font-mono" : ""}`}>{value}</p>
        </div>
    );
}

/* -------------------- TRIALS TAB -------------------- */

function TrialsTab({ trials }: { trials: Trial[] }) {
    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            {trials.length === 0 ? (
                <div className="p-6 text-center text-gray-500">
                    No trials found for this experiment.
                </div>
            ) : (
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <Th>ID</Th>
                            <Th>Name</Th>
                            <Th>Status</Th>
                            <Th>Duration</Th>
                            <Th>Created</Th>
                        </tr>
                    </thead>

                    <tbody className="bg-white divide-y divide-gray-200">
                        {trials.map((trial) => (
                            <tr key={trial.id} className="group hover:bg-indigo-50/50">
                                <Td>
                                    <Link
                                        to={`/trials/${trial.id}`}
                                        className="text-sm font-mono text-indigo-600 hover:text-indigo-800"
                                    >
                                        {trial.id}
                                    </Link>
                                </Td>
                                <Td>{trial.name}</Td>
                                <Td><StatusBadge status={trial.status} /></Td>
                                <Td>{trial.duration.toFixed(2)}s</Td>
                                <Td>{format(new Date(trial.createdAt), "MMM d, yyyy")}</Td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}

function Th({ children }: any) {
    return (
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
            {children}
        </th>
    );
}

function Td({ children }: any) {
    return <td className="px-6 py-4 whitespace-nowrap text-sm">{children}</td>;
}
