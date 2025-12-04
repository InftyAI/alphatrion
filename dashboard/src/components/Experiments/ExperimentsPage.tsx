import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useExperiments } from "../../hooks/useExperiments";
import { format } from "date-fns";
import type { Experiment } from "../../types";
import { FlaskConical, Calendar, Hash, ArrowRight, AlertCircle, Clock } from "lucide-react";

type TabType = "overview" | "list";

export default function ExperimentsPage() {
    const [searchParams] = useSearchParams();
    const projectId = searchParams.get("projectId");
    const [activeTab, setActiveTab] = useState<TabType>("overview");

    const { data: experiments, isLoading, error } = useExperiments(projectId);

    if (!projectId) {
        return (
            <div className="p-8">
                <div className="bg-amber-50/80 backdrop-blur border border-amber-200 p-5 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-amber-800 font-medium">No project selected</p>
                        <p className="text-amber-700 text-sm mt-1">
                            Please select a project from the sidebar to view experiments.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-full">
                <div className="relative">
                    <div className="w-12 h-12 border-4 border-indigo-200 rounded-full animate-spin border-t-indigo-600"></div>
                    <FlaskConical className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-5 text-indigo-600" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8">
                <div className="bg-red-50/80 backdrop-blur border border-red-200 p-5 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                    <div>
                        <p className="text-red-800 font-medium">Error loading experiments</p>
                        <p className="text-red-600 text-sm mt-1">{error.message}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                        <FlaskConical className="w-5 h-5 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900">Experiments</h1>
                </div>
                <p className="text-gray-500 text-sm ml-[52px]">
                    Project: <code className="px-2 py-0.5 bg-gray-100 rounded-md text-xs font-mono">{projectId}</code>
                </p>
            </div>

            {/* Tabs */}
            <div className="mb-6">
                <div className="inline-flex p-1 bg-gray-100/80 rounded-xl">
                    <button
                        onClick={() => setActiveTab("overview")}
                        className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === "overview"
                            ? "bg-white text-gray-900 shadow-sm"
                            : "text-gray-500 hover:text-gray-700"
                            }`}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab("list")}
                        className={`px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === "list"
                            ? "bg-white text-gray-900 shadow-sm"
                            : "text-gray-500 hover:text-gray-700"
                            }`}
                    >
                        List
                        <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-200 text-gray-600">
                            {experiments?.length ?? 0}
                        </span>
                    </button>
                </div>
            </div>

            {/* Tab Content */}
            {activeTab === "overview" ? (
                <OverviewSection experiments={experiments ?? []} />
            ) : (
                <ListTable experiments={experiments ?? []} />
            )}
        </div>
    );
}

// Overview Section - Cards + Recent Table
function OverviewSection({ experiments }: { experiments: Experiment[] }) {
    const latestExp = experiments.length > 0 ? experiments[0] : null;
    const oldestExp = experiments.length > 0 ? experiments[experiments.length - 1] : null;
    const recentExperiments = experiments.slice(0, 5);

    const stats = [
        {
            label: "Total Experiments",
            value: String(experiments.length),
            icon: Hash,
            color: "indigo",
            link: null,
        },
        {
            label: "Latest Experiment",
            value: latestExp?.name || "Unnamed",
            icon: FlaskConical,
            color: "emerald",
            link: latestExp ? `/experiments/${latestExp.id}` : null,
        },
        {
            label: "Oldest Experiment",
            value: oldestExp?.name || "Unnamed",
            icon: Calendar,
            color: "purple",
            link: oldestExp ? `/experiments/${oldestExp.id}` : null,
        },
    ];

    const colorClasses: Record<string, { bg: string; shadow: string }> = {
        indigo: { bg: "from-indigo-500 to-indigo-600", shadow: "shadow-indigo-500/20" },
        emerald: { bg: "from-emerald-500 to-emerald-600", shadow: "shadow-emerald-500/20" },
        purple: { bg: "from-purple-500 to-purple-600", shadow: "shadow-purple-500/20" },
    };

    return (
        <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {stats.map((stat, index) => {
                    const Icon = stat.icon;
                    const colors = colorClasses[stat.color];

                    const CardContent = (
                        <>
                            <div className="flex items-start justify-between mb-4">
                                <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${colors.bg} flex items-center justify-center shadow-lg ${colors.shadow}`}>
                                    <Icon className="w-5 h-5 text-white" />
                                </div>
                                {stat.link && (
                                    <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 group-hover:translate-x-1 transition-all" />
                                )}
                            </div>
                            <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
                            <p className="text-xl font-bold text-gray-900 break-words" title={stat.value}>
                                {stat.value}
                            </p>
                        </>
                    );

                    if (stat.link) {
                        return (
                            <Link
                                key={index}
                                to={stat.link}
                                className="group bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl p-6 
                                hover:shadow-xl hover:shadow-gray-200/50 transition-all duration-300 hover:-translate-y-1 block"
                            >
                                {CardContent}
                            </Link>
                        );
                    }

                    return (
                        <div
                            key={index}
                            className="bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl p-6"
                        >
                            {CardContent}
                        </div>
                    );
                })}
            </div>

            {/* Recent Experiments Table */}
            <div className="bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200/50 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <h3 className="font-semibold text-gray-900">Recent Experiments</h3>
                    <span className="text-xs text-gray-400">(Latest 5)</span>
                </div>

                {recentExperiments.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        No experiments yet
                    </div>
                ) : (
                    <table className="min-w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    Name
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    Description
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                    Created
                                </th>
                                <th className="px-6 py-3"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {recentExperiments.map((exp) => (
                                <tr
                                    key={exp.id}
                                    className="group hover:bg-indigo-50/50 transition-colors cursor-pointer"
                                    onClick={() => window.location.href = `/experiments/${exp.id}`}
                                >
                                    <td className="px-6 py-4">
                                        <span className="text-sm font-medium text-gray-900">
                                            {exp.name || "Unnamed Experiment"}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-sm text-gray-500 line-clamp-1">
                                            {exp.description || "-"}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-500">
                                            {format(new Date(exp.createdAt), "MMM d, yyyy")}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-indigo-500 inline-block" />
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

// List Table Component
function ListTable({ experiments }: { experiments: Experiment[] }) {
    if (experiments.length === 0) {
        return (
            <div className="bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl p-12 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4">
                    <FlaskConical className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-gray-500 font-medium">No experiments found</p>
                <p className="text-gray-400 text-sm mt-1">Create your first experiment to get started</p>
            </div>
        );
    }

    return (
        <div className="bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl overflow-hidden">
            <table className="min-w-full">
                <thead>
                    <tr className="border-b border-gray-200/50">
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            ID
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Name
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Description
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                            Created
                        </th>
                        <th className="px-6 py-4"></th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                    {experiments.map((exp) => (
                        <tr
                            key={exp.id}
                            className="group hover:bg-indigo-50/50 transition-colors"
                        >
                            <td className="px-6 py-4 whitespace-nowrap">
                                <Link
                                    to={`/experiments/${exp.id}`}
                                    className="text-sm font-mono text-indigo-600 hover:text-indigo-800 transition-colors"
                                >
                                    {exp.id}
                                </Link>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="text-sm font-medium text-gray-900">
                                    {exp.name || "Unnamed Experiment"}
                                </span>
                            </td>
                            <td className="px-6 py-4">
                                <span className="text-sm text-gray-500 line-clamp-1 max-w-xs">
                                    {exp.description || "-"}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="text-sm text-gray-500">
                                    {format(new Date(exp.createdAt), "MMM d, yyyy")}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right">
                                <Link
                                    to={`/experiments/${exp.id}`}
                                    className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-indigo-600 transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    View
                                    <ArrowRight size={14} />
                                </Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}