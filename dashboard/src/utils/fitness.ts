/**
 * Formats fitness values for display
 * Handles single values, arrays, and dictionaries (multi-objective)
 */
export function formatFitness(fitness: number | number[] | Record<string, number> | null): string {
    if (fitness === null || fitness === undefined) {
        return "N/A";
    }

    // Dictionary (multi-objective fitness)
    if (typeof fitness === 'object' && !Array.isArray(fitness)) {
        const entries = Object.entries(fitness)
            .map(([key, value]) => `${key}: ${value.toFixed(4)}`)
            .join(", ");
        return entries || "N/A";
    }

    // Array (multi-dimensional fitness)
    if (Array.isArray(fitness)) {
        return fitness.map(f => f.toFixed(4)).join(", ");
    }

    // Single value
    return fitness.toFixed(4);
}

/**
 * Extracts a single numeric value from fitness for plotting
 * For dictionaries/arrays, returns the first value
 */
export function getFitnessValue(fitness: number | number[] | Record<string, number> | null): number {
    if (fitness === null || fitness === undefined) {
        return 0;
    }

    // Dictionary (multi-objective) - use first value
    if (typeof fitness === 'object' && !Array.isArray(fitness)) {
        const values = Object.values(fitness);
        return values.length > 0 ? values[0] : 0;
    }

    // Array (multi-dimensional) - use first value
    if (Array.isArray(fitness)) {
        return fitness.length > 0 ? fitness[0] : 0;
    }

    // Single value
    return fitness;
}

/**
 * Type guard to check if fitness is multi-objective (dict)
 */
export function isMultiObjectiveFitness(
    fitness: number | number[] | Record<string, number> | null
): fitness is Record<string, number> {
    return fitness !== null && typeof fitness === "object" && !Array.isArray(fitness);
}

/**
 * Get fitness value for a specific key (for multi-objective)
 * Falls back to first value if key not found
 */
export function getFitnessValueForKey(
    fitness: number | number[] | Record<string, number> | null,
    key: string | null
): number {
    if (fitness === null || fitness === undefined) {
        return 0;
    }

    if (isMultiObjectiveFitness(fitness)) {
        if (key && key in fitness) {
            return fitness[key];
        }
        const values = Object.values(fitness);
        return values.length > 0 ? values[0] : 0;
    }

    if (Array.isArray(fitness)) {
        return fitness.length > 0 ? fitness[0] : 0;
    }

    return fitness;
}

/**
 * Extract all unique fitness keys from a list of snapshots
 */
export function extractFitnessKeys(
    fitnessValues: Array<number | number[] | Record<string, number> | null>
): string[] {
    const keys = new Set<string>();
    fitnessValues.forEach((fitness) => {
        if (isMultiObjectiveFitness(fitness)) {
            Object.keys(fitness).forEach((k) => keys.add(k));
        }
    });
    return Array.from(keys).sort();
}

/**
 * Extract display name from fitness key
 * e.g., "registration/fitness/accuracy" -> "accuracy"
 */
export function getKeyDisplayName(key: string): string {
    const parts = key.split("/");
    return parts[parts.length - 1];
}

/**
 * Compute weighted average of fitness values.
 * Weights must be non-negative (negative weights are treated as 0).
 */
export function evaluateWeightedAverage(
    fitness: Record<string, number>,
    weights: Record<string, number>
): number {
    let sum = 0;
    for (const [key, value] of Object.entries(fitness)) {
        const weight = Math.max(0, weights[key] ?? 0);
        sum += weight * value;
    }
    return sum;
}

/**
 * Create initial weights (all ones) for all fitness keys
 */
export function createInitialWeights(keys: string[]): Record<string, number> {
    const weights: Record<string, number> = {};
    for (const key of keys) {
        weights[key] = 1;
    }
    return weights;
}

/**
 * Compute the maximum fitness from a list of fitness values.
 * For multi-objective, returns the fitness dict with max first objective.
 */
export function computeMaxFitness(
    fitnessValues: Array<number | number[] | Record<string, number> | null>
): number | number[] | Record<string, number> | null {
    if (fitnessValues.length === 0) {
        return null;
    }

    let maxFitness: number | number[] | Record<string, number> | null = null;
    let maxValue = -Infinity;

    for (const fitness of fitnessValues) {
        const value = getFitnessValue(fitness);
        if (value > maxValue) {
            maxValue = value;
            maxFitness = fitness;
        }
    }

    return maxFitness;
}

/**
 * Format fitness for brief display (first objective only for multi-objective)
 */
export function formatFitnessBrief(fitness: number | number[] | Record<string, number> | null): string {
    if (fitness === null || fitness === undefined) {
        return "N/A";
    }

    // For all types, just show the first value
    const value = getFitnessValue(fitness);
    return value.toFixed(4);
}

/**
 * Get the first objective key from multi-objective fitness
 */
export function getFirstObjectiveKey(fitness: number | number[] | Record<string, number> | null): string | null {
    if (isMultiObjectiveFitness(fitness)) {
        const keys = Object.keys(fitness);
        return keys.length > 0 ? keys[0] : null;
    }
    return null;
}

/**
 * Compute the Pareto frontier for multi-objective optimization.
 * A point is Pareto-optimal if no other point dominates it
 * (i.e., no other point is better or equal in all objectives and strictly better in at least one).
 *
 * By default, assumes higher values are better for all objectives.
 */
export function computeParetoFrontier<T>(
    items: T[],
    getFitness: (item: T) => Record<string, number>,
    objectives: string[],
    maximize: boolean = true
): T[] {
    if (items.length === 0 || objectives.length === 0) {
        return [];
    }

    const dominated = new Set<number>();

    for (let i = 0; i < items.length; i++) {
        if (dominated.has(i)) continue;

        const fitnessA = getFitness(items[i]);

        for (let j = 0; j < items.length; j++) {
            if (i === j || dominated.has(j)) continue;

            const fitnessB = getFitness(items[j]);

            // Check if B dominates A
            let bDominatesA = true;
            let bStrictlyBetter = false;

            for (const obj of objectives) {
                const valA = fitnessA[obj] ?? 0;
                const valB = fitnessB[obj] ?? 0;

                if (maximize) {
                    if (valB < valA) {
                        bDominatesA = false;
                        break;
                    }
                    if (valB > valA) {
                        bStrictlyBetter = true;
                    }
                } else {
                    if (valB > valA) {
                        bDominatesA = false;
                        break;
                    }
                    if (valB < valA) {
                        bStrictlyBetter = true;
                    }
                }
            }

            if (bDominatesA && bStrictlyBetter) {
                dominated.add(i);
                break;
            }
        }
    }

    return items.filter((_, index) => !dominated.has(index));
}
