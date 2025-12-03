import { createContext, useContext, useState, ReactNode } from "react";

interface ProjectContextType {
    projectId: string | null;
    setProjectId: (id: string | null) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export function ProjectProvider({ children }: { children: ReactNode }) {
    const [projectId, setProjectId] = useState<string | null>(null);

    return (
        <ProjectContext.Provider value={{ projectId, setProjectId }}>
            {children}
        </ProjectContext.Provider>
    );
}

export function useProjectContext() {
    const context = useContext(ProjectContext);
    if (context === undefined) {
        throw new Error("useProjectContext must be used within a ProjectProvider");
    }
    return context;
}