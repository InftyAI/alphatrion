import { Link, useParams } from "react-router-dom";
import { useRun } from "../../hooks/use-runs";
import { format } from "date-fns";
import { useState } from "react";
import Tabs from "../ui/tabs";
import Breadcrumb from "../ui/breadcrumb";
import { formatId } from "../../utils/format";


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

export default function RunDetail() {
    const { id } = useParams<{ id: string }>();
    const { data: run, isLoading, error } = useRun(id ?? null);

    const [activeTab, setActiveTab] = useState<"overview">("overview");

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

    if (!run) {
        return (
            <div className="p-6">
                <div className="bg-yellow-50 p-4 rounded">
                    <p className="text-yellow-800">Run not found.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Breadcrumb */}
            <Breadcrumb
                items={[
                    {
                        label: "Experiments",
                        href: `/experiments?projectId=${run.projectId}`,
                    },
                    {
                        label: formatId(run.experimentId),
                        href: `/experiments/${run.experimentId}`,
                    },
                    { label: "Trials" },
                    {
                        label: formatId(run.trialId),
                        href: `/trials/${run.trialId}`,
                    },
                    { label: "Runs" },
                    {
                        label: formatId(run.id),
                    },
                ]}
            />

            {/* Header */}
            <div className="mb-6 flex items-center gap-4">
                <h1 className="text-2xl font-bold text-gray-900">Run Detail</h1>
                <StatusBadge status={run.status} />
            </div>

            {/* Tabs */}
            <Tabs
                tabs={[
                    { id: "overview", label: "Overview" },
                ]}
                active={activeTab}
                onChange={(id) => setActiveTab(id as "overview")}
            />



            {/* Tab Content */}
            <RunOverview run={run} />
        </div>
    );
}

/* Overview Section Component */

function RunOverview({ run }: { run: any }) {
    return (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Run Info</h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                    <p className="text-sm text-gray-500">ID</p>
                    <p className="text-sm font-mono">{run.id}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">Trial ID</p>
                    <p className="text-sm font-mono">{run.trialId}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">Experiment ID</p>
                    <p className="text-sm font-mono">{run.experimentId}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-500">Created</p>
                    <p className="text-sm">{format(new Date(run.createdAt), "MMM d, yyyy HH:mm")}</p>
                </div>
            </div>

            {run.meta && Object.keys(run.meta).length > 0 && (
                <div className="mt-4">
                    <p className="text-sm text-gray-500 mb-2">Metadata</p>
                    <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                        {JSON.stringify(run.meta, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}


