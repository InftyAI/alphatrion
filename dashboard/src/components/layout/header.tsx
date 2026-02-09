import { Link, useLocation, useParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { TeamSwitcher } from './team-switcher';
import { useProject } from '../../hooks/use-projects';
import { useExperiment } from '../../hooks/use-experiments';
import { useRun } from '../../hooks/use-runs';
import { truncateId } from '../../lib/format';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Header() {
  const location = useLocation();
  const params = useParams();

  // Fetch data based on current route - only fetch if we have valid IDs
  const paths = location.pathname.split('/').filter(Boolean);

  // Check if we're on a detail page (not a list page)
  const projectId = paths[0] === 'projects' && paths[1] && paths[1] !== 'projects' ? paths[1] : undefined;
  const experimentId = paths[0] === 'experiments' && paths[1] && paths[1] !== 'compare' ? paths[1] : undefined;
  const runId = paths[0] === 'runs' && paths[1] ? paths[1] : undefined;

  // Only fetch if we have valid IDs (not empty strings)
  const { data: project } = useProject(projectId || '', { enabled: !!projectId });
  const { data: experiment } = useExperiment(experimentId || '', { enabled: !!experimentId });
  const { data: run } = useRun(runId || '', { enabled: !!runId });

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
    if (paths[0] === 'projects') {
      breadcrumbs.push({ label: 'Projects', href: '/projects' });

      if (projectId && project) {
        breadcrumbs.push({
          label: truncateId(project.id),
          href: `/projects/${project.id}`
        });
      }
    } else if (paths[0] === 'experiments') {
      if (experimentId && experiment) {
        // Show full hierarchy: Projects > projectId > Experiments > experimentId
        breadcrumbs.push({ label: 'Projects', href: '/projects' });
        breadcrumbs.push({
          label: truncateId(experiment.projectId),
          href: `/projects/${experiment.projectId}`
        });
        breadcrumbs.push({ label: 'Experiments', href: `/projects/${experiment.projectId}` });
        breadcrumbs.push({
          label: truncateId(experiment.id),
          href: paths.length === 2 ? undefined : `/experiments/${experiment.id}`
        });
      } else {
        breadcrumbs.push({ label: 'Experiments', href: undefined });
      }
    } else if (paths[0] === 'runs') {
      if (runId && run) {
        // Show full hierarchy: Projects > projectId > Experiments > experimentId > Runs > runId
        breadcrumbs.push({ label: 'Projects', href: '/projects' });
        breadcrumbs.push({
          label: truncateId(run.projectId),
          href: `/projects/${run.projectId}`
        });
        breadcrumbs.push({ label: 'Experiments', href: `/projects/${run.projectId}` });
        breadcrumbs.push({
          label: truncateId(run.experimentId),
          href: `/experiments/${run.experimentId}`
        });
        breadcrumbs.push({ label: 'Runs', href: `/experiments/${run.experimentId}` });
        breadcrumbs.push({ label: truncateId(run.id), href: undefined });
      } else {
        breadcrumbs.push({ label: 'Runs', href: undefined });
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
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      {/* Breadcrumbs */}
      <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
        {breadcrumbs.map((crumb, index) => (
          <div key={index} className="flex items-center">
            {index > 0 && (
              <ChevronRight className="mx-2 h-4 w-4" />
            )}
            {crumb.href ? (
              <Link
                to={crumb.href}
                className="hover:text-foreground transition-colors"
              >
                {crumb.label}
              </Link>
            ) : (
              <span>
                {crumb.label}
              </span>
            )}
          </div>
        ))}
      </nav>

      {/* Team Switcher */}
      <TeamSwitcher />
    </header>
  );
}
