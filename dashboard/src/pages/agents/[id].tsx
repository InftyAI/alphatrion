import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MessageSquare, Calendar, Clock, Bot } from 'lucide-react';
import { useAgent } from '../../hooks/use-agents';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';
import type { Status, Session, AgentType } from '../../types';
import { graphqlQuery } from '../../lib/graphql-client';

const getAgentTypeLabel = (type: AgentType): string => {
  if (type === 1 || String(type).toUpperCase() === 'CLAUDE') {
    return 'Claude';
  }
  return 'Unknown';
};

const STATUS_VARIANTS: Record<Status, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'unknown' | 'info'> = {
  UNKNOWN: 'unknown',
  PENDING: 'warning',
  RUNNING: 'info',
  CANCELLED: 'secondary',
  COMPLETED: 'success',
  FAILED: 'destructive',
};

interface AgentSessionsResponse {
  agent: {
    sessions: Session[];
  };
}

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: agent, isLoading: agentLoading, error: agentError } = useAgent(id!);

  // Fetch sessions for this agent
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    const fetchSessions = async () => {
      setSessionsLoading(true);
      try {
        const data = await graphqlQuery<AgentSessionsResponse>(
          `query GetAgentSessions($id: ID!) {
            agent(id: $id) {
              sessions(page: 0, pageSize: 1000) {
                id
                agentId
                teamId
                userId
                meta
                createdAt
                updatedAt
              }
            }
          }`,
          { id }
        );
        const fetchedSessions = data.agent?.sessions || [];
        // Sort sessions by created time (newest first)
        fetchedSessions.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        setSessions(fetchedSessions);
      } catch (error) {
        console.error('Failed to fetch agent sessions:', error);
        setSessions([]);
      } finally {
        setSessionsLoading(false);
      }
    };

    fetchSessions();
  }, [id]);

  if (agentLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (agentError || !agent) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Bot className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Agent not found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              The requested agent could not be found.
            </p>
            <Button onClick={() => navigate('/agents')}>
              Back to Agents
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <Bot className="h-6 w-6 text-purple-600" />
            <h1 className="text-xl font-semibold tracking-tight">{agent.name}</h1>
            <Badge variant="outline" className="text-xs">
              {getAgentTypeLabel(agent.type)}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 flex flex-col">
        <div className="mb-3">
          <h2 className="text-base font-semibold text-foreground">Sessions</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            All conversation sessions for this agent
          </p>
        </div>

        {sessionsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <Card className="flex-1">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                <MessageSquare className="h-8 w-8 text-muted-foreground/60" />
              </div>
              <p className="text-sm font-medium text-foreground">No sessions found</p>
              <p className="text-xs text-muted-foreground mt-1">
                Sessions will appear here when you use Claude Code
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 overflow-y-auto">
              {sessions.map((session) => {
                const projectName = session.meta?.project_name as string | undefined;

                return (
                  <Card
                    key={session.id}
                    className="hover:shadow-lg transition-all cursor-pointer border hover:border-blue-200"
                    onClick={() => navigate(`/sessions/${session.id}`)}
                  >
                    <CardHeader className="p-4 pb-3">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2.5 min-w-0 flex-1">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/20">
                            <MessageSquare className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <CardTitle className="text-sm font-semibold truncate">
                              {projectName || 'Session'}
                            </CardTitle>
                            <p className="text-[11px] font-mono text-muted-foreground truncate mt-0.5">
                              {session.id}
                            </p>
                          </div>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent className="p-4 pt-0 space-y-2">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3 shrink-0" />
                        <span className="truncate">
                          {formatDistanceToNow(new Date(session.createdAt), { addSuffix: true })}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3 shrink-0" />
                        <span className="truncate">
                          Updated {formatDistanceToNow(new Date(session.updatedAt), { addSuffix: true })}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

          </>
        )}
      </div>
    </div>
  );
}
