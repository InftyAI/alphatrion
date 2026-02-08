import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Network, AlertCircle, ExternalLink } from 'lucide-react';

export function TracingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Distributed Tracing</h1>
        <p className="mt-2 text-muted-foreground">
          OpenTelemetry integration and trace visualization
        </p>
      </div>

      {/* Status Card */}
      <Card className="border-yellow-500/50 bg-yellow-50/50 dark:bg-yellow-950/20">
        <CardHeader>
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-yellow-600 dark:text-yellow-500" />
            <div>
              <CardTitle>Feature Coming Soon</CardTitle>
              <CardDescription>This feature is planned for Phase 2</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The tracing UI requires backend changes to persist span data. Currently,
            traces are exported to console only.
          </p>
        </CardContent>
      </Card>

      {/* Current Limitations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            Current Implementation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-semibold text-sm mb-2">What Works Now</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>OpenTelemetry SDK integration in backend</li>
              <li>Automatic span creation for key operations</li>
              <li>Console export of trace data</li>
              <li>Trace context propagation</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-sm mb-2">What's Missing</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>Persistent storage of span data in database</li>
              <li>GraphQL API for querying traces</li>
              <li>Waterfall visualization (D3.js)</li>
              <li>Span search and filtering</li>
              <li>Service dependency graph</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Phase 2 Roadmap */}
      <Card>
        <CardHeader>
          <CardTitle>Phase 2 Roadmap</CardTitle>
          <CardDescription>Planned features for future release</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <Badge className="mt-0.5">Backend</Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">Span Persistence</p>
                <p className="text-sm text-muted-foreground">
                  Store spans in PostgreSQL with indexed queries for fast retrieval
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Badge className="mt-0.5">Backend</Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">Trace Query API</p>
                <p className="text-sm text-muted-foreground">
                  GraphQL queries for fetching traces, spans, and dependencies
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Badge variant="secondary" className="mt-0.5">
                Frontend
              </Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">D3.js Waterfall View</p>
                <p className="text-sm text-muted-foreground">
                  Interactive timeline showing span hierarchy and timing
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Badge variant="secondary" className="mt-0.5">
                Frontend
              </Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">Search & Filters</p>
                <p className="text-sm text-muted-foreground">
                  Filter by service, operation, duration, and custom attributes
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Badge variant="secondary" className="mt-0.5">
                Frontend
              </Badge>
              <div className="flex-1">
                <p className="text-sm font-medium">Service Map</p>
                <p className="text-sm text-muted-foreground">
                  Visualize service dependencies and request flows
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* External Tools */}
      <Card>
        <CardHeader>
          <CardTitle>Using External Tools</CardTitle>
          <CardDescription>
            For immediate tracing needs, use these tools
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <p className="font-medium text-sm">Jaeger</p>
              <p className="text-sm text-muted-foreground">
                Open-source distributed tracing platform
              </p>
            </div>
            <a
              href="https://www.jaegertracing.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline flex items-center gap-1 text-sm"
            >
              Learn More
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <p className="font-medium text-sm">Zipkin</p>
              <p className="text-sm text-muted-foreground">
                Distributed tracing system
              </p>
            </div>
            <a
              href="https://zipkin.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline flex items-center gap-1 text-sm"
            >
              Learn More
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
