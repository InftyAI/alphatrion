import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Agent } from '../types';

interface AgentsResponse {
  agents: Agent[];
}

interface AgentResponse {
  agent: Agent | null;
}

export function useAgents(
  teamId: string,
  options?: {
    page?: number;
    pageSize?: number;
    enabled?: boolean;
  }
) {
  const { page = 0, pageSize = 20, enabled = true } = options || {};

  return useQuery<Agent[]>({
    queryKey: ['agents', teamId, page, pageSize],
    queryFn: async () => {
      const data = await graphqlQuery<AgentsResponse>(queries.listAgents, {
        teamId,
        page,
        pageSize,
      });
      return data.agents || [];
    },
    enabled: enabled && !!teamId,
  });
}

export function useAgent(agentId: string, options?: { enabled?: boolean }) {
  const { enabled = true } = options || {};

  return useQuery<Agent | null>({
    queryKey: ['agent', agentId],
    queryFn: async () => {
      const data = await graphqlQuery<AgentResponse>(queries.getAgent, {
        id: agentId,
      });
      return data.agent;
    },
    enabled: enabled && !!agentId,
  });
}
