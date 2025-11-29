import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { format } from 'date-fns';
import apiService from '../../services/api';

export default function TrialDetail() {
    const { id } = useParams<{ id: string }>();
    const trialId = parseInt(id || '0');

    // State for search, sort, and filter  
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState<'created_at' | 'costs' | 'tokens' | 'latency_ms'>('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [costFilter, setCostFilter] = useState<'all' | 'high' | 'low'>('all');

    // Fetch trial details
    const { data: trial, isLoading: trialLoading } = useQuery({
        queryKey: ['trial', trialId],
        queryFn: () => apiService.getTrialDetails(trialId),
        enabled: !!trialId,
    });

    // Fetch runs for this trial
    const { data: runsData, isLoading: runsLoading } = useQuery({
        queryKey: ['trial-runs', trialId],
        queryFn: () => apiService.getTrialRuns(trialId),
        enabled: !!trialId,
    });



    

    // Process runs with search and filters 
    const processedRuns = useMemo(() => {
        if (!runsData?.runs) return [];

        let filtered = [...runsData.runs];

        // Apply search
        if (searchTerm) {
            filtered = filtered.filter(run =>
                run.id?.toString().includes(searchTerm) ||
                run.tokens?.toString().includes(searchTerm)
            );
        }

        // Apply cost filter
        if (costFilter === 'high') {
            const avgCost = runsData.stats?.total_cost / runsData.runs.length;
            filtered = filtered.filter(run => run.costs > avgCost);
        } else if (costFilter === 'low') {
            const avgCost = runsData.stats?.total_cost / runsData.runs.length;
            filtered = filtered.filter(run => run.costs <= avgCost);
        }

        // Apply sorting 
        filtered.sort((a, b) => {
            const aVal = a[sortBy] || 0;
            const bVal = b[sortBy] || 0;
            return sortOrder === 'asc' ?
                (aVal > bVal ? 1 : -1) :
                (aVal < bVal ? 1 : -1);
        });

        return filtered;
    }, [runsData, searchTerm, sortBy, sortOrder, costFilter]);

    // Calculate statistics 
    const stats = useMemo(() => {
        if (!runsData?.runs || runsData.runs.length === 0) {
            return {
                avgTokens: 0,
                avgCost: 0,
                avgLatency: 0,
                totalRuns: 0,
                totalCost: 0,
                totalTokens: 0,
                minLatency: 0,
                maxLatency: 0,
                costPerToken: 0
            };
        }

        const runs = runsData.runs;
        const totalRuns = runs.length;
        const totalTokens = runs.reduce((sum, r) => sum + (r.tokens || 0), 0);
        const totalCost = runs.reduce((sum, r) => sum + (r.costs || 0), 0);
        const totalLatency = runs.reduce((sum, r) => sum + (r.latency_ms || 0), 0);

        return {
            avgTokens: Math.round(totalTokens / totalRuns),
            avgCost: totalCost / totalRuns,
            avgLatency: Math.round(totalLatency / totalRuns),
            totalRuns,
            totalCost,
            totalTokens,
            minLatency: Math.min(...runs.map(r => r.latency_ms || 0)),
            maxLatency: Math.max(...runs.map(r => r.latency_ms || 0)),
            costPerToken: totalTokens > 0 ? totalCost / totalTokens : 0
        };
    }, [runsData]);

    const StatusBadge = ({ status }: { status: string }) => {
        const colors: Record<string, string> = {
            pending: 'bg-yellow-100 text-yellow-800',
            running: 'bg-blue-100 text-blue-800',
            finished: 'bg-green-100 text-green-800',
            failed: 'bg-red-100 text-red-800',
        };
        return (
            <span className={`px-2 py-1 text-xs rounded-full ${colors[status]}`}>
                {status}
            </span>
        );
    };

    if (trialLoading || runsLoading) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (!trial) {
        return (
            <div className="p-6">
                <div className="bg-red-50 p-4 rounded">
                    <p className="text-red-600">Trial not found</p>
                </div>
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
                    <li>
                        <Link
                            to={`/experiments/${trial.experiment_id}`}
                            className="text-primary-600 hover:text-primary-800"
                        >
                            {trial.experiment_name || `Experiment ${trial.experiment_id}`}
                        </Link>
                    </li>
                    <li className="text-gray-400">/</li>
                    <li className="text-gray-700 font-medium">Trial #{trial.id}</li>
                </ol>
            </nav>

            {/* Header */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <div className="flex justify-between items-start">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Trial #{trial.id}</h1>
                        <div className="mt-2 flex items-center gap-4">
                            <StatusBadge status={trial.status} />
                            {trial.accuracy && (
                                <span className="text-sm text-gray-600">
                                    Accuracy: <strong>{(trial.accuracy * 100).toFixed(1)}%</strong>
                                </span>
                            )}
                            {trial.duration_seconds && (
                                <span className="text-sm text-gray-600">
                                    Duration: <strong>{trial.duration_seconds}s</strong>
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-gray-500 mt-2">
                            Created: {format(new Date(trial.created_at), 'PPP')}
                        </p>
                    </div>
                </div>
            </div>

            {/* Table 1: Run Statistics */}
            <div className="bg-white rounded-lg shadow mb-6">
                <div className="px-6 py-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">Run Statistics</h2>
                </div>
                <div className="p-6">
                    <div className="grid grid-cols-3 gap-6">
                        {/* Average Tokens */}
                        <div className="bg-blue-50 rounded-lg p-4">
                            <div className="text-sm font-medium text-blue-600">Average Tokens</div>
                            <div className="text-2xl font-bold text-gray-900 mt-1">
                                {stats.avgTokens.toLocaleString()}
                            </div>
                            <div className="text-xs text-gray-500 mt-2">
                                Total: {stats.totalTokens.toLocaleString()} tokens
                            </div>
                        </div>

                        {/* Average Cost */}
                        <div className="bg-green-50 rounded-lg p-4">
                            <div className="text-sm font-medium text-green-600">Average Cost</div>
                            <div className="text-2xl font-bold text-gray-900 mt-1">
                                ${stats.avgCost.toFixed(4)}
                            </div>
                            <div className="text-xs text-gray-500 mt-2">
                                Total: ${stats.totalCost.toFixed(2)} | Per token: ${stats.costPerToken.toFixed(6)}
                            </div>
                        </div>

                        {/* Average Latency */}
                        <div className="bg-purple-50 rounded-lg p-4">
                            <div className="text-sm font-medium text-purple-600">Average Latency</div>
                            <div className="text-2xl font-bold text-gray-900 mt-1">
                                {stats.avgLatency}ms
                            </div>
                            <div className="text-xs text-gray-500 mt-2">
                                Min: {stats.minLatency}ms | Max: {stats.maxLatency}ms
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Table 2: Runs List with Search/Filter/Sort */}
            <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b">
                    <h2 className="text-lg font-semibold text-gray-900">
                        Runs ({processedRuns.length} of {runsData?.runs?.length || 0})
                    </h2>
                </div>

                {/* Search and Filter Bar */}
                <div className="px-6 py-4 border-b bg-gray-50">
                    <div className="flex gap-4">
                        {/* Search */}
                        <div className="flex-1">
                            <input
                                type="text"
                                placeholder="Search by ID or tokens..."
                                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>

                        {/* Cost Filter */}
                        <select
                            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            value={costFilter}
                            onChange={(e) => setCostFilter(e.target.value as any)}
                        >
                            <option value="all">All Costs</option>
                            <option value="high">Above Average</option>
                            <option value="low">Below Average</option>
                        </select>

                        {/* Sort By */}
                        <select
                            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value as any)}
                        >
                            <option value="created_at">Date</option>
                            <option value="costs">Cost</option>
                            <option value="tokens">Tokens</option>
                            <option value="latency_ms">Latency</option>
                        </select>

                        {/* Sort Order */}
                        <button
                            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                            className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            {sortOrder === 'asc' ? '↑' : '↓'}
                        </button>
                    </div>
                </div>

                {/* Runs Table */}
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Run ID
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Tokens
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Cost
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Latency
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Cost/Token
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Created
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {processedRuns.map((run: any) => (
                                <tr key={run.id || Math.random()} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        #{run.id || 'N/A'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {run.tokens?.toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        ${run.costs?.toFixed(4)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {run.latency_ms}ms
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        ${run.tokens > 0 ? (run.costs / run.tokens).toFixed(6) : '0'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {format(new Date(run.created_at), 'MMM d, HH:mm')}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {processedRuns.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                            No runs found matching your criteria
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}