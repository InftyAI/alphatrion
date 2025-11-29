// ---- Shared domain types ----
export type Experiment = {
    id: number;
    name: string;
    project_id: string;
    created_at: string;
    is_deleted: boolean;
    total_trials: number;
    total_runs: number;
    total_cost: number;
    avg_accuracy: number | null;
};

export type Trial = {
    id: number;
    experiment_id: number;
    status: "pending" | "running" | "finished" | "failed";
    created_at: string;
    accuracy: number | null;
    duration_seconds?: number | null;
    total_cost?: number;
    total_tokens?: number;
    avg_latency_ms?: number | null;
    run_count?: number;
};

export type Run = {
    id: number;
    trial_id: number;
    tokens: number;
    costs: number;
    latency_ms: number;
    created_at: string;
};

// ---- Dashboard + Charts ----
export type DashboardStats = {
    total_experiments: number;
    total_trials: number;
    total_runs: number;
    total_cost: number;
    avg_accuracy: number | null;
    avg_latency_ms: number | null;
    active_trials: number;
    failed_trials: number;
    success_rate: number;
};

export type CostByExperiment = {
    experiment_id: number;
    experiment_name: string;
    total_cost: number;
    percentage: number;
    run_count: number;
};

export type DailyCost = {
    date: string; // 'YYYY-MM-DD'
    total_cost: number;
    run_count: number;
    experiment_count: number;
};

export type AccuracyPoint = {
    trial_id: number;
    timestamp: string; // ISO
    accuracy: number;  // 0..1
    status: "pending" | "running" | "finished" | "failed";
};


// ---- Chat Types ----
export type ChatMessage = {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
};

export type ChatRequest = {
    message: string;
    context: {
        experiments?: Experiment[];
        trials?: Trial[];
        runs?: Run[];
        [key: string]: any;
    };
};

export type ChatResponse = {
    response: string;
    context_used: string[];
    relevant_experiments: string[];
};