import { useQuery } from '@tanstack/react-query';
import { graphqlQuery, queries } from '../lib/graphql-client';
import type { Organization } from '../types';

interface GetOrganizationResponse {
  organization: Organization | null;
}

/**
 * Hook to fetch organization by ID
 */
export function useOrganization(orgId: string | undefined) {
  return useQuery({
    queryKey: ['organization', orgId],
    queryFn: async () => {
      if (!orgId) return null;
      const data = await graphqlQuery<GetOrganizationResponse>(
        queries.getOrganization,
        { id: orgId }
      );
      return data.organization;
    },
    enabled: !!orgId,
    staleTime: 10 * 60 * 1000, // 10 minutes - organizations don't change often
  });
}
