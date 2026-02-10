import { useSearchParams } from 'react-router-dom';
import { useExperimentsByIds } from '../../hooks/use-experiments';
import { useGroupedMetrics } from '../../hooks/use-metrics';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { ParameterDiff } from '../../components/comparison/parameter-diff';
import { MetricsOverlay } from '../../components/comparison/metrics-overlay';
import type { Status } from '../../types';

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'default',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

export function ExperimentComparePage() {
  const [searchParams] = useSearchParams();
  const experimentIds = searchParams.get('ids')?.split(',') || [];

  const { data: experiments, isLoading } = useExperimentsByIds(experimentIds);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!experiments || experiments.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Experiment Comparison</CardTitle>
          <CardDescription>
            Select at least 2 experiments to compare
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            No experiments selected for comparison
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Experiment Comparison
        </h1>
        <p className="mt-2 text-muted-foreground">
          Comparing {experiments.length} experiments
        </p>
      </div>

      {/* Experiment Overview Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {experiments.map((experiment) => (
          <Card key={experiment.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-lg">{experiment.name}</CardTitle>
                <Badge variant={STATUS_VARIANTS[experiment.status]}>
                  {experiment.status}
                </Badge>
              </div>
              {experiment.description && (
                <CardDescription>{experiment.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Duration</dt>
                  <dd className="font-medium">
                    {experiment.duration > 0
                      ? `${experiment.duration.toFixed(2)}s`
                      : 'N/A'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Params</dt>
                  <dd className="font-medium">
                    {experiment.params
                      ? Object.keys(experiment.params).length
                      : 0}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Parameter Comparison */}
      <ParameterDiff experiments={experiments} />

      {/* Metrics Overlay */}
      <MetricsOverlay experimentIds={experimentIds} />
    </div>
  );
}
