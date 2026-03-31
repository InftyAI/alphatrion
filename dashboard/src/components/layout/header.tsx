import { Link, useLocation } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { UserProfile } from './user-profile';
import { useExperiment } from '../../hooks/use-experiments';
import { useRun } from '../../hooks/use-runs';
import { useAgent } from '../../hooks/use-agents';
import { useTeam } from '../../hooks/use-teams';
import { useTeamContext } from '../../context/team-context';
import { graphqlQuery } from '../../lib/graphql-client';
import { truncateId } from '../../lib/format';
import { useQuery } from '@tanstack/react-query';
import type { Session } from '../../types';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Header() {
  const location = useLocation();
  const { selectedTeamId } = useTeamContext();

  // Fetch current team
  const { data: currentTeam } = useTeam(selectedTeamId);

  // Fetch data based on current route - only fetch if we have valid IDs
  const paths = location.pathname.split('/').filter(Boolean);

  // Check if we're on a detail page (not a list page)
  const experimentId = paths[0] === 'experiments' && paths[1] && paths[1] !== 'compare' ? paths[1] : undefined;
  const runId = paths[0] === 'runs' && paths[1] ? paths[1] : undefined;
  const agentId = paths[0] === 'agents' && paths[1] ? paths[1] : undefined;
  const sessionId = paths[0] === 'sessions' && paths[1] ? paths[1] : undefined;

  // Only fetch if we have valid IDs (not empty strings)
  const { data: experiment } = useExperiment(experimentId || '', { enabled: !!experimentId });
  const { data: run } = useRun(runId || '', { enabled: !!runId });
  const { data: agent } = useAgent(agentId || '', { enabled: !!agentId });

  // Fetch session data
  const { data: session } = useQuery<Session>({
    queryKey: ['session', sessionId],
    queryFn: async () => {
      const data = await graphqlQuery<{ session: Session }>(
        `query GetSession($sessionId: ID!) {
          session(sessionId: $sessionId) {
            id
            agentId
            teamId
            userId
            meta
            createdAt
            updatedAt
          }
        }`,
        { sessionId: sessionId }
      );
      return data.session;
    },
    enabled: !!sessionId,
  });

  // Generate breadcrumbs from pathname
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const paths = location.pathname.split('/').filter(Boolean);

    if (paths.length === 0) {
      return [{ label: 'Home' }];
    }

    const breadcrumbs: BreadcrumbItem[] = [
      { label: 'Home', href: '/' },
    ];

    // Handle different route patterns
    if (paths[0] === 'experiments') {
      if (experimentId && experiment) {
        breadcrumbs.push({ label: 'Experiments', href: '/experiments' });
        breadcrumbs.push({
          label: truncateId(experiment.id),
          href: paths.length === 2 ? undefined : `/experiments/${experiment.id}`
        });
      } else {
        breadcrumbs.push({ label: 'Experiments', href: undefined });
      }
    } else if (paths[0] === 'runs') {
      if (runId && run) {
        // Show hierarchy: Experiments > experimentId > Runs > runId
        breadcrumbs.push({ label: 'Experiments', href: '/experiments' });
        breadcrumbs.push({
          label: truncateId(run.experimentId),
          href: `/experiments/${run.experimentId}`
        });
        breadcrumbs.push({ label: 'Runs', href: `/experiments/${run.experimentId}` });
        breadcrumbs.push({ label: truncateId(run.id), href: undefined });
      } else {
        breadcrumbs.push({ label: 'Runs', href: undefined });
      }
    } else if (paths[0] === 'agents') {
      if (agentId && agent && paths[1]) {
        breadcrumbs.push({ label: 'Agents', href: '/agents' });
        breadcrumbs.push({ label: truncateId(agent.id), href: undefined });
      } else {
        breadcrumbs.push({ label: 'Agents', href: undefined });
      }
    } else if (paths[0] === 'sessions') {
      if (sessionId) {
        // Show hierarchy: Agents > agentId > Sessions > sessionId
        breadcrumbs.push({ label: 'Agents', href: '/agents' });
        if (session) {
          breadcrumbs.push({
            label: truncateId(session.agentId),
            href: `/agents/${session.agentId}`
          });
          breadcrumbs.push({ label: 'Sessions', href: `/agents/${session.agentId}` });
          breadcrumbs.push({ label: truncateId(session.id), href: undefined });
        } else {
          // Still loading - show with sessionId from URL
          breadcrumbs.push({ label: '...', href: undefined });
          breadcrumbs.push({ label: 'Sessions', href: undefined });
          breadcrumbs.push({ label: truncateId(sessionId), href: undefined });
        }
      } else {
        breadcrumbs.push({ label: 'Sessions', href: undefined });
      }
    } else {
      // Default handling for other routes
      paths.forEach((path, index) => {
        const currentPath = '/' + paths.slice(0, index + 1).join('/');
        const isLast = index === paths.length - 1;
        const label = path.charAt(0).toUpperCase() + path.slice(1);

        breadcrumbs.push({
          label,
          href: isLast ? undefined : currentPath,
        });
      });
    }

    return breadcrumbs;
  };

  const breadcrumbs = generateBreadcrumbs();

  return (
    <header className="flex h-14 items-center justify-between bg-card px-6">
      {/* Breadcrumbs */}
      <nav className="flex items-center space-x-2 text-sm">
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          return (
            <div key={index} className="flex items-center">
              {index > 0 && (
                <ChevronRight className="mx-2 h-4 w-4 text-muted-foreground" />
              )}
              {crumb.href && !isLast ? (
                <Link
                  to={crumb.href}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-foreground font-medium">
                  {crumb.label}
                </span>
              )}
            </div>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="flex items-center">
        <UserProfile />
      </div>
    </header>
  );
}
