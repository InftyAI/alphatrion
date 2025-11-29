import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import type { DashboardStats, CostByExperiment, DailyCost } from "../types";

export function useDashboard(days = 30) {
    const stats = useQuery<DashboardStats>({
        queryKey: ["dashboard", "stats"],
        queryFn: () => api.getDashboardStats(),
        staleTime: 60_000,
    });

    const costBreakdown = useQuery<CostByExperiment[]>({
        queryKey: ["dashboard", "cost-breakdown"],
        queryFn: () => api.getCostBreakdown(),
        staleTime: 60_000,
    });

    const dailyCosts = useQuery<DailyCost[]>({
        queryKey: ["dashboard", "daily-costs", days],
        queryFn: () => api.getDailyCosts(days),
        staleTime: 60_000,
    });

    return { stats, costBreakdown, dailyCosts };
}
