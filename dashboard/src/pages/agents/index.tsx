import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Search } from 'lucide-react';
import { useTeamContext } from '../../context/team-context';
import { useAgents } from '../../hooks/use-agents';
import { AgentType } from '../../types';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { formatDistanceToNow } from 'date-fns';

const getAgentTypeLabel = (type: AgentType): string => {
  if (type === AgentType.CLAUDE || type === 1 || String(type).toUpperCase() === 'CLAUDE') {
    return 'Claude';
  }
  return 'Unknown';
};

const PAGE_SIZE = 20;

export function AgentsPage() {
  const navigate = useNavigate();
  const { selectedTeamId } = useTeamContext();
  const [currentPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: agents, isLoading } = useAgents(selectedTeamId || '', {
    page: currentPage,
    pageSize: PAGE_SIZE,
    enabled: !!selectedTeamId,
  });

  const filteredAgents = agents?.filter(agent =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    agent.description?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="space-y-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Agents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            View and manage your agent registry
          </p>
        </div>

        {/* Search */}
        <div className="relative w-80">
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-9 text-[13px] font-medium focus:bg-blue-50 focus:border-blue-300 focus-visible:ring-0"
          />
        </div>
      </div>

      {/* Agent Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : !filteredAgents || filteredAgents.length === 0 ? (
        <Card className="flex-1 flex flex-col">
          <CardContent className="flex-1 flex flex-col items-center justify-center text-center py-16">
            <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-muted-foreground/60" />
            </div>
            <p className="text-sm font-medium text-foreground">
              {searchQuery ? 'No agents match your search' : 'No agents found'}
            </p>
            <p className="text-xs text-muted-foreground mt-1 max-w-md">
              {searchQuery
                ? 'Try a different search term'
                : 'Run alphatrion run claude to create your first agent'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAgents.map((agent) => (
            <Card
              key={agent.id}
              className="hover:shadow-lg transition-all cursor-pointer border hover:border-blue-200"
              onClick={() => navigate(`/agents/${agent.id}`)}
            >
              <CardHeader className="p-4 pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/20">
                      <Bot className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base font-semibold truncate">
                          {agent.name}
                        </CardTitle>
                        <Badge variant="outline" className="text-xs">
                          {getAgentTypeLabel(agent.type)}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 font-mono truncate">
                        {agent.id}
                      </p>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                {agent.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {agent.description}
                  </p>
                )}
                <div className="text-xs text-muted-foreground">
                  Created {formatDistanceToNow(new Date(agent.createdAt), { addSuffix: true })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
