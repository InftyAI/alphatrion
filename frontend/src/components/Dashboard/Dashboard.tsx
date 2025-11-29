import { useDashboard } from "../../hooks/useDashboard";
import CostPieChart from "../Visualizations/CostPieChart";
import DailyCostChart from "../Visualizations/DailyCostChart";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
    const navigate = useNavigate();
    const { stats, costBreakdown, dailyCosts } = useDashboard(30);

    const loading =
        stats.isLoading || costBreakdown.isLoading || dailyCosts.isLoading;
    const error = stats.error || costBreakdown.error || dailyCosts.error;

    if (loading) {
        return (
            <div className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-24 rounded-lg bg-gray-100 animate-pulse" />
                    ))}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="h-80 rounded-lg bg-gray-100 animate-pulse" />
                    <div className="h-80 rounded-lg bg-gray-100 animate-pulse" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded">
                    {(error as Error).message}
                </div>
            </div>
        );
    }

    const s = stats.data!;
    const byExp = costBreakdown.data || [];
    const byDay = dailyCosts.data || [];

    return (
        <div className="p-6 space-y-6">
            {/* Stat cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard label="Experiments" value={s.total_experiments} />
                <StatCard label="Trials" value={s.total_trials} />
                <StatCard label="Runs" value={s.total_runs} />
                <StatCard label="Total Cost" value={`$${s.total_cost.toFixed(2)}`} />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="font-semibold mb-2">Cost by Experiment</h3>
                    <CostPieChart
                        data={byExp}
                        onSliceClick={(id) => navigate(`/experiments/${id}`)}
                    />
                </div>

                <div className="bg-white rounded-lg shadow p-4">
                    <h3 className="font-semibold mb-2">Daily Cost (last 30 days)</h3>
                    <DailyCostChart
                        data={byDay}
                        onBarClick={(_date) => { /* 可选：跳转到某天过滤页 */ }}
                    />
                </div>
            </div>
        </div>
    );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
    return (
        <div className="relative overflow-hidden bg-white/80 backdrop-blur-sm rounded-xl shadow-card hover:shadow-card-hover transition-all duration-300 p-6 border border-gray-100">
            {/* Gradient overlay */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary-100 to-accent-100 rounded-full blur-3xl opacity-30 -mr-16 -mt-16"></div>

            <div className="relative">
                <div className="text-sm text-gray-600 font-medium mb-1">{label}</div>
                <div className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                    {value}
                </div>
            </div>
        </div>
    );
}
