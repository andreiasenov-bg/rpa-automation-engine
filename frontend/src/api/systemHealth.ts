/**
 * Infrastructure health API client.
 * Calls the deployer's /deploy/infrastructure-health endpoint
 * which checks: auto-sync, github, docker containers, disk space.
 */
import axios from 'axios';

const DEPLOY_TOKEN = 'zHOOF6REZHaUMskB069Xmx5tCBog30axMrgqt39n0zE';

export interface AutoSyncHealth {
  status: 'ok' | 'down';
  state: string;
  pid: number;
  error?: string;
}

export interface GitHubHealth {
  status: 'ok' | 'down';
  response_ms: number;
  last_commit: string;
  last_message: string;
  last_commit_time: string;
  error?: string;
}

export interface ContainerInfo {
  name: string;
  status: string;
  state: string;
}

export interface DockerHealth {
  status: 'ok' | 'degraded' | 'down';
  containers: ContainerInfo[];
  total: number;
  all_healthy: boolean;
  response_ms: number;
  error?: string;
}

export interface DiskHealth {
  status: 'ok' | 'degraded' | 'down';
  total_gb: number;
  used_gb: number;
  free_gb: number;
  used_pct: number;
  error?: string;
}

export interface InfrastructureHealth {
  auto_sync: AutoSyncHealth;
  github: GitHubHealth;
  docker: DockerHealth;
  disk: DiskHealth;
  timestamp: string;
}

export const systemHealthApi = {
  getInfraHealth: (): Promise<InfrastructureHealth> =>
    axios
      .get('/deploy/infrastructure-health', {
        headers: { Authorization: `Bearer ${DEPLOY_TOKEN}` },
        timeout: 20000,
      })
      .then((r) => r.data),
};
