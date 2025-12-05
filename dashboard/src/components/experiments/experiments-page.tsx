import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useExperiments } from "../../hooks/use-experiments";
import { format } from "date-fns";
import type { Experiment } from "../../types";
import { FlaskConical, Calendar, Hash, AlertCircle, Clock } from "lucide-react";
import Tabs from "../ui/tabs";
import Breadcrumb from "../ui/breadcrumb";


type TabType = "overview" | "list";

export default function ExperimentsPage() {
    const [searchParams] = useSearchParams();
    const projectId = searchParams.get("projectId");
    const [activeTab, setActiveTab] = useState<TabType>("overview");

    const { data: experiments, isLoading, error } = useExperiments(projectId);

    if (!projectId) {
        return (
            <div className="p-6">
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
            <div className="p-6">
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
        <div className="p-6">
            {/* Breadcrumb */}
            <Breadcrumb items={[{ label: "Experiments" }]} />

            {/* Tabs */}
            <Tabs
                tabs={[
                    { id: "overview", label: "Overview" },
                    { id: "list", label: `Experiments (${experiments?.length ?? 0})` },
                ]}
                active={activeTab}
                onChange={(id) => setActiveTab(id as TabType)}
            />

            {/* Tab Content */}
            {activeTab === "overview" ? (
                <OverviewSection experiments={experiments ?? []} />
            ) : (
                <ListTable experiments={experiments ?? []} />
            )}
        </div>
    );
}

/* -------------------------- OVERVIEW SECTION -------------------------- */

function OverviewSection({ experiments }: { experiments: Experiment[] }) {
    const latestExp = experiments[0] ?? null;
    const oldestExp = experiments[experiments.length - 1] ?? null;
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
                                className="group bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-2xl p-6 hover:shadow-xl hover:shadow-gray-200/50 transition-all duration-300 hover:-translate-y-1 block"
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
                    <div className="p-6 text-center text-gray-500">No experiments yet</div>
                ) : (
                    <table className="min-w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                                    ID
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                                    Name
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                                    Description
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
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
                                    onClick={() => (window.location.href = `/experiments/${exp.id}`)}
                                >
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm font-mono text-indigo-600">{exp.id}</span>
                                    </td>
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
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

/* -------------------------- LIST TABLE -------------------------- */

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
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">
                            ID
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">
                            Name
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">
                            Description
                        </th>
                        <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">
                            Created
                        </th>
                        <th className="px-6 py-4"></th>
                    </tr>
                </thead>

                <tbody className="divide-y divide-gray-100">
                    {experiments.map((exp) => (
                        <tr key={exp.id} className="group hover:bg-indigo-50/50 transition-colors">
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
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
