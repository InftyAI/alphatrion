import { useQuery } from "@tanstack/react-query";
import { fetchProjects } from "../services/graphql";

export function useProjects() {
    return useQuery({
        queryKey: ["projects"],
        queryFn: () => fetchProjects(),
    });
}