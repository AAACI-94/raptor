// Typed API client for RAPTOR backend

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

// Projects
export const api = {
  // Projects
  listProjects: () => request<any[]>('/projects'),
  getProject: (id: string) => request<any>(`/projects/${id}`),
  createProject: (data: any) => request<any>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: string, data: any) => request<any>(`/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProject: (id: string) => request<any>(`/projects/${id}`, { method: 'DELETE' }),

  // Publication Targets (aliases: /publications and /venues)
  listVenues: () => request<any[]>('/publications'),
  getVenue: (id: string) => request<any>(`/publications/${id}`),

  // Pipeline
  startPipeline: (id: string) => request<any>(`/projects/${id}/pipeline/start`, { method: 'POST' }),
  advancePipeline: (id: string) => request<any>(`/projects/${id}/pipeline/advance`, { method: 'POST' }),
  rejectPipeline: (id: string, feedback: string, targetStage?: string) =>
    request<any>(`/projects/${id}/pipeline/reject`, {
      method: 'POST',
      body: JSON.stringify({ feedback, target_stage: targetStage }),
    }),
  overridePipeline: (id: string, reason: string) =>
    request<any>(`/projects/${id}/pipeline/override`, { method: 'POST', body: JSON.stringify({ reason }) }),
  getPipelineStatus: (id: string) => request<any>(`/projects/${id}/pipeline/status`),

  // Artifacts
  listArtifacts: (projectId: string) => request<any[]>(`/projects/${projectId}/artifacts`),
  getArtifact: (id: string) => request<any>(`/artifacts/${id}`),
  getLatestArtifact: (projectId: string, type: string) => request<any>(`/projects/${projectId}/artifacts/latest/${type}`),

  // Observatory
  getTraces: (projectId: string) => request<any>(`/observatory/traces/${projectId}`),
  getQuality: (projectId: string) => request<any>(`/observatory/quality/${projectId}`),
  getCost: (projectId?: string) => request<any>(`/observatory/cost${projectId ? `/${projectId}` : ''}`),
  getInsights: () => request<any>(`/observatory/insights`),
  getRubricHistory: (venueId: string) => request<any>(`/observatory/rubric-history/${venueId}`),

  // Feedback
  submitFeedback: (data: any) => request<any>('/observatory/feedback', { method: 'POST', body: JSON.stringify(data) }),

  // Preview
  getPreview: (projectId: string) => request<any>(`/projects/${projectId}/preview`),
  getFigures: (projectId: string) => request<any>(`/projects/${projectId}/figures`),

  // Diagnostics
  getDiagnostics: (projectId: string) => request<any>(`/observatory/diagnostics/${projectId}`),
  getHealingStats: () => request<any>(`/observatory/healing-stats`),

  // Health
  health: () => request<any>('/health'),
};
