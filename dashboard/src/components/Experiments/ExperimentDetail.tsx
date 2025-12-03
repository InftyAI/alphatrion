import { Link, useParams } from "react-router-dom";
import { useExperimentDetail } from "../../hooks/useExperimentDetail";
import { format } from "date-fns";
import type { Trial } from "../../types";

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

            {/* Experiment Info Card */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Experiment Info</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-sm text-gray-500">ID</p>
                        <p className="text-sm font-mono">{experiment.id}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">Project ID</p>
                        <p className="text-sm font-mono">{experiment.projectId}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">Created</p>
                        <p className="text-sm">{format(new Date(experiment.createdAt), "MMM d, yyyy HH:mm")}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">Updated</p>
                        <p className="text-sm">{format(new Date(experiment.updatedAt), "MMM d, yyyy HH:mm")}</p>
                    </div>
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

            {/* Trials Section */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">
                        Trials ({trials.length})
                    </h2>
                </div>

                {trials.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                        No trials found for this experiment.
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
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
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    ID
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {trials.map((trial: Trial) => (
                                <tr key={trial.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/trials/${trial.id}`}
                                            className="text-sm font-medium text-blue-600 hover:text-blue-900"
                                        >
                                            {trial.name}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <StatusBadge status={trial.status} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-900">
                                            {trial.duration.toFixed(2)}s
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-500">
                                            {format(new Date(trial.createdAt), "MMM d, yyyy")}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-500 font-mono">
                                            {trial.id.slice(0, 8)}...
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}