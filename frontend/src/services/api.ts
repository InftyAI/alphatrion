import axios from "axios";
import type {
    DashboardStats,
    CostByExperiment,
    DailyCost,
    Experiment,
    Trial,
    AccuracyPoint,
    ChatRequest,
    ChatResponse,
} from "../types";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE,
    timeout: 15000,
});

api.interceptors.response.use(
    (res) => res,
    (err) => {
        const msg =
            err?.response?.data?.message ||
            err?.message ||
            "Network error, please try again.";
        return Promise.reject(new Error(msg));
    }
);

export default {
    // ---- Dashboard ----
    async getDashboardStats(): Promise<DashboardStats> {
        const { data } = await api.get<DashboardStats>("/dashboard/stats");
        return data;
    },
    async getCostBreakdown(): Promise<CostByExperiment[]> {
        const { data } = await api.get<CostByExperiment[]>("/dashboard/cost-breakdown");
        return data || [];
    },
    async getDailyCosts(days = 30): Promise<DailyCost[]> {
        const { data } = await api.get<DailyCost[]>("/dashboard/daily-costs", {
            params: { days },
        });
        return data || [];
    },

    // ---- Experiments ----
    async getExperiments(params: {
        page?: number;
        page_size?: number;
        name?: string;
        sort_by?: string;
        sort_order?: "asc" | "desc";
    }): Promise<{ items: Experiment[]; total: number; page: number; page_size: number; total_pages: number }> {
        const { data } = await api.get("/experiments", { params });
        return data;
    },
    async getExperiment(id: number): Promise<Experiment> {
        const { data } = await api.get(`/experiments/${id}`);
        return data;
    },
    async getExperimentTrials(id: number): Promise<{ experiment_id: number; trials: Trial[]; total: number }> {
        const { data } = await api.get(`/experiments/${id}/trials`);
        return data;
    },
    async getAccuracyCurve(id: number): Promise<AccuracyPoint[]> {
        const { data } = await api.get<AccuracyPoint[]>(`/experiments/${id}/accuracy-curve`);
        return data || [];
    },

    // ---- Trials ----
    async getTrialRuns(trialId: number): Promise<{ trial_id: number; runs: any[]; total: number; stats: any }> {
        const { data } = await api.get(`/trials/${trialId}/runs`);
        return data;
    },

    // Add trial detail page route to applications
    async getTrialDetails(id: number): Promise<any> {
        const { data } = await api.get(`/trials/${id}`);
        return data;
    },

    // New: add the chat function
    async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
        const { data } = await api.post<ChatResponse>("/chat", request);
        return data;
    },



};

export type { Experiment };
