import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import apiService, { Experiment } from '../../services/api';
import { format } from 'date-fns';

export default function Experiments() {
    const [page, setPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    const { data, isLoading, error } = useQuery({
        queryKey: ['experiments', page, searchTerm, sortBy, sortOrder],
        queryFn: () =>
            apiService.getExperiments({
                page,
                page_size: 20,
                name: searchTerm || undefined,
                sort_by: sortBy,
                sort_order: sortOrder,
            }),
    });

    const handleSort = (field: string) => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder('desc');
        }
    };

    const StatusBadge = ({ status }: { status?: string }) => {
        const colors: Record<string, string> = {
            active: 'bg-green-100 text-green-800',
            completed: 'bg-blue-100 text-blue-800',
            failed: 'bg-red-100 text-red-800',
        };

        return (
            <span
                className={`px-2 py-1 text-xs rounded-full ${colors[status || 'active'] || colors.active
                    }`}
            >
                {status || 'active'}
            </span>
        );
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="bg-red-50 p-4 rounded">
                    <p className="text-red-600">Error loading experiments</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Experiments</h1>
                <p className="text-gray-600">Manage and analyze your ML experiments</p>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
                <div className="flex gap-4">
                    <div className="flex-1">
                        <input
                            type="text"
                            placeholder="Search experiments..."
                            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <select
                        className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                    >
                        <option value="created_at">Created Date</option>
                        <option value="name">Name</option>
                        <option value="total_cost">Total Cost</option>
                    </select>
                    <button
                        onClick={() => handleSort(sortBy)}
                        className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        {sortOrder === 'asc' ? '↑' : '↓'}
                    </button>
                </div>
            </div>

            {/* Experiments Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            {/* Name column - clickable header for sorting */}
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('name')}
                            >
                                Name {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Project
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Trials
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Runs
                            </th>
                            {/* Cost column - clickable header for sorting */}
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('total_cost')}
                            >
                                Cost {sortBy === 'total_cost' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Accuracy
                            </th>
                            {/* Created Date column - clickable header for sorting */}
                            <th
                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('created_at')}
                            >
                                Created {sortBy === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                            </th>
                            {/* REMOVED: Actions column - no longer needed since name is clickable */}
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100">
                            ID
                        </th>

                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {data?.items.map((experiment: Experiment) => (
                        <tr key={experiment.id} className="hover:bg-gray-50">
                            {/* MODIFIED: Name is now a clickable link to experiment details */}
                            <td className="px-6 py-4 whitespace-nowrap">
                                <Link
                                    to={`/experiments/${experiment.id}`}
                                    className="text-sm font-medium text-primary-600 hover:text-primary-900"
                                >
                                    {experiment.name}
                                </Link>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-500">{experiment.project_id}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-900">{experiment.total_trials || 0}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-900">{experiment.total_runs || 0}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-900">
                                    ${experiment.total_cost?.toFixed(2) || '0.00'}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-900">
                                    {experiment.avg_accuracy
                                        ? `${(experiment.avg_accuracy * 100).toFixed(1)}%`
                                        : '-'}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="text-sm text-gray-500">
                                    {format(new Date(experiment.created_at), 'MMM d, yyyy')}
                                </div>
                            </td>
                            {/* REMOVED: "View Details →" link - redundant since name is now clickable */}
                        </tr>
                    ))}
                </tbody>
            </table>

            {/* Pagination */}
            {data && data.total_pages > 1 && (
                <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
                    <div className="flex-1 flex justify-between sm:hidden">
                        <button
                            onClick={() => setPage(Math.max(1, page - 1))}
                            disabled={page === 1}
                            className="px-4 py-2 border rounded-md disabled:opacity-50"
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                            disabled={page === data.total_pages}
                            className="px-4 py-2 border rounded-md disabled:opacity-50"
                        >
                            Next
                        </button>
                    </div>
                    <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                        <div>
                            <p className="text-sm text-gray-700">
                                Showing page <span className="font-medium">{page}</span> of{' '}
                                <span className="font-medium">{data.total_pages}</span> (
                                <span className="font-medium">{data.total}</span> total experiments)
                            </p>
                        </div>
                        <div>
                            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                                {[...Array(Math.min(5, data.total_pages))].map((_, i) => {
                                    const pageNum = i + 1;
                                    return (
                                        <button
                                            key={pageNum}
                                            onClick={() => setPage(pageNum)}
                                            className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${page === pageNum
                                                ? 'z-10 bg-primary-50 border-primary-500 text-primary-600'
                                                : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                                                }`}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                            </nav>
                        </div>
                    </div>
                </div>
            )}
        </div>
        </div >
    );
}