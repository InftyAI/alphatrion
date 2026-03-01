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
  repoName: string
): Promise<string[]> {
  try {
    const data = await graphqlQuery<{ artifactTags: Array<{ name: string }> }>(
      queries.listArtifactTags,
      { team_id: teamId, repo_name: repoName }
    );
    return data.artifactTags.map(tag => tag.name);
  } catch (error) {
    throw new Error(`Failed to list tags for repository ${repoName}: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get artifact content
 */
export async function getArtifactContent(
  teamId: string,
  tag: string,
  repoName: string
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
      { team_id: teamId, tag, repo_name: repoName }
    );
    return data.artifactContent;
  } catch (error) {
    throw new Error(`Failed to get artifact content: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Parse repository name from full path
 * Expected format: team
 */
export function parseRepositoryPath(fullPath: string): { team: string } | null {
  const parts = fullPath.split('/');
  if (parts.length !== 1) {
    return null;
  }
  return {
    team: parts[0],
  };
}
