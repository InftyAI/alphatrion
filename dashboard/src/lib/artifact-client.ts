import { graphqlQuery, queries } from './graphql-client';

/**
 * Artifact client using GraphQL API
 */

/**
 * List all repositories in the ORAS registry
 */
export async function listRepositories(): Promise<string[]> {
  try {
    const data = await graphqlQuery<{ artifactRepos: Array<{ name: string }> }>(
      queries.listArtifactRepositories
    );
    return data.artifactRepos.map(repo => repo.name);
  } catch (error) {
    throw new Error(`Failed to list repositories: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * List tags for a specific repository
 */
export async function listTags(
  teamId: string,
  projectId: string,
  repoType?: 'execution' | 'checkpoint'
): Promise<string[]> {
  try {
    const data = await graphqlQuery<{ artifactTags: Array<{ name: string }> }>(
      queries.listArtifactTags,
      { team_id: teamId, project_id: projectId, repo_type: repoType }
    );
    return data.artifactTags.map(tag => tag.name);
  } catch (error) {
    throw new Error(`Failed to list tags for project ${projectId}: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get artifact content
 */
export async function getArtifactContent(
  teamId: string,
  projectId: string,
  tag: string,
  repoType?: 'execution' | 'checkpoint'
): Promise<{ filename: string; content: string; contentType: string }> {
  try {
    const data = await graphqlQuery<{
      artifactContent: {
        filename: string;
        content: string;
        contentType: string;
      }
    }>(
      queries.getArtifactContent,
      { team_id: teamId, project_id: projectId, tag, repo_type: repoType }
    );
    return data.artifactContent;
  } catch (error) {
    throw new Error(`Failed to get artifact content: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Parse repository name from full path
 * Expected format: team/project
 */
export function parseRepositoryPath(fullPath: string): { team: string; project: string } | null {
  const parts = fullPath.split('/');
  if (parts.length !== 2) {
    return null;
  }
  return {
    team: parts[0],
    project: parts[1],
  };
}
