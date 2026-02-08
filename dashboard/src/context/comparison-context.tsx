import { createContext, useContext, useState, ReactNode } from 'react';
import type { ComparisonState } from '../types';

const ComparisonContext = createContext<ComparisonState | undefined>(undefined);

export function ComparisonProvider({ children }: { children: ReactNode }) {
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<string[]>([]);

  const addExperiment = (id: string) => {
    if (!selectedExperimentIds.includes(id)) {
      setSelectedExperimentIds([...selectedExperimentIds, id]);
    }
  };

  const removeExperiment = (id: string) => {
    setSelectedExperimentIds(selectedExperimentIds.filter((expId) => expId !== id));
  };

  const clearSelection = () => {
    setSelectedExperimentIds([]);
  };

  return (
    <ComparisonContext.Provider
      value={{
        selectedExperimentIds,
        addExperiment,
        removeExperiment,
        clearSelection,
      }}
    >
      {children}
    </ComparisonContext.Provider>
  );
}

export function useComparison() {
  const context = useContext(ComparisonContext);
  if (!context) {
    throw new Error('useComparison must be used within ComparisonProvider');
  }
  return context;
}
