import { Link, useParams } from "react-router-dom";
import { useTrialDetail } from "../../hooks/use-trial-detail";
import { format } from "date-fns";
import type { Run, Metric } from "../../types";
import { useSelection } from "../../pages/app";
import { useEffect, useState } from "react";
import Tabs from "../ui/tabs";
import Breadcrumb from "../ui/breadcrumb";
import { formatId } from "../../utils/format";

/* ----------------------------- STATUS BADGE ----------------------------- */
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

/* ----------------------------- METRICS CHART ----------------------------- */
function MetricsChart({ metrics }: { metrics: Metric[] }) {
    if (metrics.length === 0) {
        return <div className="text-center text-gray-500 py-8">No metrics data available.</div>;
    }

    const metricsByKey: Record<string, Metric[]> = {};
    metrics.forEach((m) => {
        const key = m.key || "unknown";
        if (!metricsByKey[key]) metricsByKey[key] = [];
        metricsByKey[key].push(m);
    });

    Object.values(metricsByKey).forEach((arr) => arr.sort((a, b) => a.step - b.step));
    const keys = Object.keys(metricsByKey);

    return (
        <div>
            <div className="mb-4 text-sm text-gray-600">
                Found {metrics.length} metric points across {keys.length} metric(s): {keys.join(", ")}
            </div>

            {keys.map((key) => {
                const data = metricsByKey[key];
                const values = data.map((d) => d.value ?? 0);
                const minVal = Math.min(...values);
                const maxVal = Math.max(...values);
                const range = maxVal - minVal || 1;

                return (
                    <div key={key} className="mb-6">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">{key}</h4>
                        <div className="bg-gray-50 p-4 rounded">
                            <svg viewBox="0 0 400 100" className="w-full h-32">
                                <line x1="40" y1="10" x2="40" y2="90" stroke="#e5e7eb" strokeWidth="1" />
                                <line x1="40" y1="90" x2="390" y2="90" stroke="#e5e7eb" strokeWidth="1" />

                                <text x="35" y="15" textAnchor="end" className="text-xs fill-gray-500">
                                    {maxVal.toFixed(2)}
                                </text>
                                <text x="35" y="92" textAnchor="end" className="text-xs fill-gray-500">
                                    {minVal.toFixed(2)}
                                </text>

                                <polyline
                                    fill="none"
                                    stroke="#3b82f6"
                                    strokeWidth="2"
                                    points={data
                                        .map((d, i) => {
                                            const x = 40 + (i / (data.length - 1 || 1)) * 350;
                                            const y = 90 - (((d.value ?? 0) - minVal) / range) * 80;
                                            return `${x},${y}`;
                                        })
                                        .join(" ")}
                                />

                                {data.map((d, i) => {
                                    const x = 40 + (i / (data.length - 1 || 1)) * 350;
                                    const y = 90 - (((d.value ?? 0) - minVal) / range) * 80;
                                    return <circle key={i} cx={x} cy={y} r="3" fill="#3b82f6" />;
                                })}
                            </svg>

                            <div className="flex gap-4 mt-2 text-xs text-gray-500">
                                <span>Steps: {data.length}</span>
                                <span>Min: {minVal.toFixed(4)}</span>
                                <span>Max: {maxVal.toFixed(4)}</span>
                                <span>Latest: {(data[data.length - 1]?.value ?? 0).toFixed(4)}</span>
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/* ----------------------------- TRIAL DETAIL PAGE ----------------------------- */
export default function TrialDetail() {
    const { id } = useParams<{ id: string }>();
    const { trial, runs, metrics, isLoading, error } = useTrialDetail(id ?? null);
    const { setExperimentId, setTrialId } = useSelection();

    const [activeTab, setActiveTab] = useState<"overview" | "runs">("overview");

    useEffect(() => {
        if (trial) {
            setExperimentId(trial.experimentId);
            setTrialId(trial.id);
        }
    }, [trial, setExperimentId, setTrialId]);

    if (isLoading) return <div className="flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
    </div>;

    if (error) return (
        <div className="p-6">
            <div className="bg-red-50 p-4 rounded">
                <p className="text-red-600">Error: {error.message}</p>
            </div>
        </div>
    );

    if (!trial) return (
        <div className="p-6">
            <div className="bg-yellow-50 p-4 rounded">
                <p className="text-yellow-800">Trial not found.</p>
            </div>
        </div>
    );

    return (
        <div className="p-6">
            {/* Breadcrumb */}
            <Breadcrumb
                items={[
                    {
                        label: "Experiments",
                        href: `/experiments?projectId=${trial.projectId}`,
                    },
                    {
                        label: formatId(trial.experimentId),
                        href: `/experiments/${trial.experimentId}`,
                    },
                    { label: "Trials" },
                    {
                        label: formatId(trial.id),
                    },
                ]}
            />


            {/* Header */}
            {/* Name and Description */}
            <div className="mb-6">
                <div className="flex items-center gap-4">
                    <h1 className="text-2xl font-bold text-gray-900">{trial.name}</h1>
                    <StatusBadge status={trial.status} />
                </div>
                {trial.description && (
                    <p className="text-gray-600 mt-1">{trial.description}</p>
                )}
            </div>

            {/* ----------------------------- Tabs ----------------------------- */}
            <Tabs
                tabs={[
                    { id: "overview", label: "Overview" },
                    { id: "runs", label: `Runs (${runs.length})` },
                ]}
                active={activeTab}
                onChange={(id) => setActiveTab(id as any)}
            />

            {/* ----------------------------- OVERVIEW ----------------------------- */}
            {activeTab === "overview" && (
                <>
                    <div className="bg-white rounded-lg shadow p-6 mb-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">Trial Info</h2>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                                <p className="text-sm text-gray-500">ID</p>
                                <p className="text-sm font-mono">{trial.id}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Duration</p>
                                <p className="text-sm">{trial.duration.toFixed(2)}s</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Created</p>
                                <p className="text-sm">{format(new Date(trial.createdAt), "MMM d, yyyy HH:mm")}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Updated</p>
                                <p className="text-sm">{format(new Date(trial.updatedAt), "MMM d, yyyy HH:mm")}</p>
                            </div>
                        </div>

                        {trial.params && Object.keys(trial.params).length > 0 && (
                            <div className="mt-4">
                                <p className="text-sm text-gray-500 mb-2">Parameters</p>
                                <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                                    {JSON.stringify(trial.params, null, 2)}
                                </pre>
                            </div>
                        )}

                        {trial.meta && Object.keys(trial.meta).length > 0 && (
                            <div className="mt-4">
                                <p className="text-sm text-gray-500 mb-2">Metadata</p>
                                <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                                    {JSON.stringify(trial.meta, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>

                    {/* Metrics merged into overview */}
                    <div className="bg-white rounded-lg shadow p-6 mb-6">
                        <h2 className="text-lg font-semibold text-gray-900 mb-4">
                            Metrics ({metrics.length} points)
                        </h2>
                        <MetricsChart metrics={metrics} />
                    </div>
                </>
            )}

            {/* ----------------------------- RUNS ----------------------------- */}
            {activeTab === "runs" && (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                    <div className="px-6 py-4 border-b">
                        <h2 className="text-lg font-semibold text-gray-900">Runs ({runs.length})</h2>
                    </div>

                    {runs.length === 0 ? (
                        <div className="p-6 text-center text-gray-500">No runs found for this trial.</div>
                    ) : (
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                        ID
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                        Created
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {runs.map((run: Run) => (
                                    <tr key={run.id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Link
                                                to={`/runs/${run.id}`}
                                                className="text-sm font-mono text-blue-600 hover:text-blue-900"
                                            >
                                                {run.id}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <StatusBadge status={run.status} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-sm text-gray-500">
                                                {format(new Date(run.createdAt), "MMM d, yyyy HH:mm")}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    );
}
