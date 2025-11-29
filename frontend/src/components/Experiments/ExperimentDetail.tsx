import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import apiService from '../../services/api';
import AccuracyCurve from '../Visualizations/AccuracyCurve';
import { format } from 'date-fns';

export default function ExperimentDetail() {
    const { id } = useParams<{ id: string }>();
    const experimentId = parseInt(id || '0');

    //  NEW: Filter states
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [minAccuracy, setMinAccuracy] = useState<number>(0);
    const [searchId, setSearchId] = useState<string>('');
    const [sortBy, setSortBy] = useState<string>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    const { data: experiment } = useQuery({
        queryKey: ['experiment', experimentId],
        queryFn: () => apiService.getExperiment(experimentId),
        enabled: !!experimentId,
    });

    const { data: trialsData } = useQuery({
        queryKey: ['experiment-trials', experimentId],
        queryFn: () => apiService.getExperimentTrials(experimentId),
        enabled: !!experimentId,
    });

    const { data: accuracyData } = useQuery({
        queryKey: ['accuracy-curve', experimentId],
        queryFn: () => apiService.getAccuracyCurve(experimentId),
        enabled: !!experimentId,
    });

    //  NEW: Filter and sort trials
    const filteredTrials = useMemo(() => {
        if (!trialsData?.trials) return [];

        let filtered = [...trialsData.trials];

        // Filter by status
        if (statusFilter !== 'all') {
            filtered = filtered.filter(t => t.status === statusFilter);
        }

        // Filter by accuracy
        if (minAccuracy > 0) {
            filtered = filtered.filter(t => {
                if (!t.accuracy) return false;
                return (t.accuracy * 100) >= minAccuracy;
            });
        }

        // Filter by trial ID search
        if (searchId) {
            filtered = filtered.filter(t =>
                t.id.toString().includes(searchId)
            );
        }

        // Sort
        filtered.sort((a, b) => {
            let aVal: any = a[sortBy as keyof typeof a];
            let bVal: any = b[sortBy as keyof typeof b];

            // Handle null/undefined
            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;

            // Convert dates to timestamps for comparison
            if (sortBy === 'created_at') {
                aVal = new Date(aVal).getTime();
                bVal = new Date(bVal).getTime();
            }

            if (sortOrder === 'asc') {
                return aVal > bVal ? 1 : -1;
            } else {
                return aVal < bVal ? 1 : -1;
            }
        });

        return filtered;
    }, [trialsData, statusFilter, minAccuracy, searchId, sortBy, sortOrder]);

    // NEW: Reset filters function
    const resetFilters = () => {
        setStatusFilter('all');
        setMinAccuracy(0);
        setSearchId('');
        setSortBy('created_at');
        setSortOrder('desc');
    };

    const StatusBadge = ({ status }: { status: string }) => {
        const colors: Record<string, string> = {
            pending: 'bg-yellow-100 text-yellow-800',
            running: 'bg-blue-100 text-blue-800',
            finished: 'bg-green-100 text-green-800',
            failed: 'bg-red-100 text-red-800',
        };

        return (
            <span className={`px-2 py-1 text-xs rounded-full ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
                {status}
            </span>
        );
    };

    // Helper function to safely format dates
    const formatDate = (dateString: string | null | undefined, formatStr: string) => {
        if (!dateString) return 'N/A';
        try {
            return format(new Date(dateString), formatStr);
        } catch {
            return 'Invalid date';
        }
    };

    if (!experiment || !trialsData) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Breadcrumb */}
            <nav className="mb-4">
                <ol className="flex items-center space-x-2">
                    <li>
                        <Link to="/experiments" className="text-primary-600 hover:text-primary-800">
                            Experiments
                        </Link>
                    </li>
                    <li className="text-gray-400">/</li>
                    <li className="text-gray-700 font-medium">{experiment.name}</li>
                </ol>
            </nav>

            {/* Header */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{experiment.name}</h1>
                        <p className="text-gray-600 mt-1">Project: {experiment.project_id}</p>
                        <p className="text-sm text-gray-500 mt-2">
                            Created: {formatDate(experiment.created_at, 'PPP')}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-3xl font-bold text-primary-600">
                            ${experiment.total_cost?.toFixed(2) || '0.00'}
                        </p>
                        <p className="text-sm text-gray-500">Total Cost</p>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t">
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.total_trials || 0}
                        </p>
                        <p className="text-sm text-gray-500">Total Trials</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.total_runs || 0}
                        </p>
                        <p className="text-sm text-gray-500">Total Runs</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {experiment.avg_accuracy
                                ? `${(experiment.avg_accuracy * 100).toFixed(1)}%`
                                : '-'}
                        </p>
                        <p className="text-sm text-gray-500">Avg Accuracy</p>
                    </div>
                    <div>
                        <p className="text-2xl font-semibold text-gray-900">
                            {trialsData.trials.filter(t => t.status === 'finished').length}
                        </p>
                        <p className="text-sm text-gray-500">Completed Trials</p>
                    </div>
                </div>
            </div>

            {/* Accuracy Curve */}
            {accuracyData && accuracyData.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Accuracy Curve</h2>
                    <AccuracyCurve data={accuracyData} />
                </div>
            )}

            {/*  NEW: Filter Bar */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-medium text-gray-700">Filter Trials</h3>
                    <button
                        onClick={resetFilters}
                        className="text-xs text-primary-600 hover:text-primary-800 font-medium"
                    >
                        Reset All
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Status Filter */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Status
                        </label>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        >
                            <option value="all">All Statuses</option>
                            <option value="finished">Finished</option>
                            <option value="running">Running</option>
                            <option value="pending">Pending</option>
                            <option value="failed">Failed</option>
                        </select>
                    </div>

                    {/* Accuracy Filter */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Min Accuracy: {minAccuracy}%
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            step="5"
                            value={minAccuracy}
                            onChange={(e) => setMinAccuracy(parseInt(e.target.value))}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
                        />
                    </div>

                    {/* Search by ID */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Search Trial ID
                        </label>
                        <input
                            type="text"
                            placeholder="e.g., 1, 2, 10"
                            value={searchId}
                            onChange={(e) => setSearchId(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                    </div>

                    {/* Sort By */}
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                            Sort By
                        </label>
                        <div className="flex gap-2">
                            <select
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value)}
                                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                            >
                                <option value="created_at">Created</option>
                                <option value="accuracy">Accuracy</option>
                                <option value="total_cost">Cost</option>
                                <option value="duration_seconds">Duration</option>
                            </select>
                            <button
                                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                                className="px-3 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
                                title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
                            >
                                {sortOrder === 'asc' ? '↑' : '↓'}
                            </button>
                        </div>
                    </div>
                </div>

                {/*  NEW: Results count */}
                <div className="mt-3 text-xs text-gray-500">
                    Showing {filteredTrials.length} of {trialsData.trials.length} trials
                </div>
            </div>

            {/* Trials Table */}
            <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">Trials</h2>
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Trial ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Status
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Accuracy
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Duration
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Runs
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Cost
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Created
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {/* MODIFIED: Use filteredTrials instead of trialsData.trials */}
                        {filteredTrials.length > 0 ? (
                            filteredTrials.map((trial) => (
                                <tr key={trial.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        <Link
                                            to={`/trials/${trial.id}`}
                                            className="text-primary-600 hover:text-primary-900"
                                        >
                                            #{trial.id}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <StatusBadge status={trial.status} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {trial.accuracy ? `${(trial.accuracy * 100).toFixed(1)}%` : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {trial.duration_seconds ? `${trial.duration_seconds}s` : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {trial.total_runs || 0}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        ${trial.total_cost?.toFixed(2) || '0.00'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {formatDate(trial.created_at, 'MMM d, HH:mm')}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">
                                    No trials match the current filters
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}