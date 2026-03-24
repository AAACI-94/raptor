import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Play, ChevronRight, RotateCcw, Shield, AlertCircle, CheckCircle2, Loader2, Download, Eye, Code, Image } from 'lucide-react';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import DocumentPreview from '../components/DocumentPreview';
import FigurePreview from '../components/FigurePreview';
import type { Project, PipelineStatus, PipelineEvent } from '../types';

const STAGES = [
  { key: 'TOPIC_SELECTED', label: 'Topic & Venue', agent: null },
  { key: 'RESEARCHING', label: 'Research', agent: 'research_strategist' },
  { key: 'STRUCTURING', label: 'Structure', agent: 'structure_architect' },
  { key: 'DRAFTING', label: 'Drafting', agent: 'domain_writer' },
  { key: 'ILLUSTRATING', label: 'Figures', agent: 'visual_architect' },
  { key: 'REVIEWING', label: 'Review', agent: 'critical_reviewer' },
  { key: 'PRODUCING', label: 'Production', agent: 'production_agent' },
  { key: 'PUBLISHED', label: 'Published', agent: null },
];

function getStageIndex(status: string): number {
  // Order matters: more specific replacements first
  const s = status
    .replace('PRODUCTION_COMPLETE', 'PUBLISHED')
    .replace('ILLUSTRATION_COMPLETE', 'REVIEWING')
    .replace('REVIEW_PASSED', 'PRODUCING')
    .replace('REVISION_REQUESTED', 'REVIEWING')
    .replace('_COMPLETE', '');
  return STAGES.findIndex((st) => st.key === s || status.startsWith(st.key));
}

export default function Workspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [latestArtifact, setLatestArtifact] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'preview' | 'figures' | 'artifacts'>('preview');

  const { events, connected } = useWebSocket(projectId || null);

  // Fetch project and pipeline status
  useEffect(() => {
    if (!projectId) return;
    Promise.all([api.getProject(projectId), api.getPipelineStatus(projectId).catch(() => null)])
      .then(([p, ps]) => { setProject(p); setPipeline(ps); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  // Update on WebSocket events
  useEffect(() => {
    if (!projectId || events.length === 0) return;
    const last = events[events.length - 1];
    if (last.event === 'agent_completed' || last.event === 'pipeline_stage_changed') {
      api.getProject(projectId).then(setProject);
      api.getPipelineStatus(projectId).then(setPipeline).catch(() => {});
      if (last.artifact_id) {
        api.getArtifact(last.artifact_id).then(setLatestArtifact).catch(() => {});
      }
    }
  }, [events, projectId]);

  const handleStart = async () => {
    if (!projectId) return;
    setActing(true);
    try {
      await api.startPipeline(projectId);
      const [p, ps] = await Promise.all([api.getProject(projectId), api.getPipelineStatus(projectId)]);
      setProject(p);
      setPipeline(ps);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActing(false);
    }
  };

  const handleAdvance = async () => {
    if (!projectId) return;
    setActing(true);
    try {
      await api.advancePipeline(projectId);
      const [p, ps] = await Promise.all([api.getProject(projectId), api.getPipelineStatus(projectId)]);
      setProject(p);
      setPipeline(ps);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActing(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-raptor-600" /></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><AlertCircle className="inline h-5 w-5 text-red-500 mr-2" />{error}</div>;
  if (!project) return <div>Project not found</div>;

  const activeStage = getStageIndex(project.status);
  const canStart = project.status === 'TOPIC_SELECTED' && project.venue_profile_id && project.topic_description;
  const canAdvance = project.status.endsWith('_COMPLETE') || project.status === 'REVIEW_PASSED';
  const isActive = project.status.endsWith('ING') && project.status !== 'TOPIC_SELECTED';
  const hasPreviewableContent = activeStage >= 2; // From STRUCTURING onward there's something to preview

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{project.title}</h1>
          <p className="text-sm text-gray-500 mt-1">{project.topic_description?.slice(0, 100)}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs text-gray-500">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Pipeline Stepper */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
        <div className="flex items-center justify-between">
          {STAGES.map((stage, i) => {
            const isCurrent = i === activeStage;
            const isDone = i < activeStage;
            return (
              <React.Fragment key={stage.key}>
                <div className={`flex flex-col items-center ${isCurrent ? 'text-raptor-600' : isDone ? 'text-green-600' : 'text-gray-400'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 ${
                    isCurrent ? 'border-raptor-600 bg-raptor-50' : isDone ? 'border-green-600 bg-green-50' : 'border-gray-300'
                  }`}>
                    {isDone ? <CheckCircle2 className="h-4 w-4" /> : isActive && isCurrent ? <Loader2 className="h-4 w-4 animate-spin" /> : i + 1}
                  </div>
                  <span className="text-xs mt-1 font-medium">{stage.label}</span>
                </div>
                {i < STAGES.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 ${i < activeStage ? 'bg-green-300' : 'bg-gray-200'}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>
        {project.revision_cycles > 0 && (
          <div className="mt-3 text-center">
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
              <RotateCcw className="inline h-3 w-3 mr-1" />
              Revision cycle {project.revision_cycles}/{pipeline?.max_revision_cycles || 3}
            </span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-3">
          {canStart && (
            <button onClick={handleStart} disabled={acting}
              className="flex items-center gap-2 px-4 py-2 bg-raptor-600 text-white rounded-lg hover:bg-raptor-700 disabled:opacity-50">
              <Play className="h-4 w-4" />{acting ? 'Starting...' : 'Start Pipeline'}
            </button>
          )}
          {canAdvance && (
            <button onClick={handleAdvance} disabled={acting}
              className="flex items-center gap-2 px-4 py-2 bg-raptor-600 text-white rounded-lg hover:bg-raptor-700 disabled:opacity-50">
              <ChevronRight className="h-4 w-4" />{acting ? 'Advancing...' : 'Advance Pipeline'}
            </button>
          )}
        </div>

        {/* View mode toggle (show once we have artifacts) */}
        {hasPreviewableContent && (
          <div className="flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('preview')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${
                viewMode === 'preview' ? 'bg-white dark:bg-gray-600 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Eye className="h-3.5 w-3.5" />Preview
            </button>
            <button
              onClick={() => setViewMode('figures')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${
                viewMode === 'figures' ? 'bg-white dark:bg-gray-600 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Image className="h-3.5 w-3.5" />Figures
            </button>
            <button
              onClick={() => setViewMode('artifacts')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${
                viewMode === 'artifacts' ? 'bg-white dark:bg-gray-600 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Code className="h-3.5 w-3.5" />Artifacts
            </button>
          </div>
        )}
      </div>

      {/* Live Events */}
      {events.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4 mb-6 max-h-48 overflow-y-auto font-mono text-xs">
          {events.map((ev, i) => (
            <div key={i} className="text-gray-300 py-0.5">
              <span className="text-gray-500">[{ev.agent || 'pipeline'}]</span>{' '}
              <span className={ev.event === 'agent_error' ? 'text-red-400' : ev.event === 'agent_completed' ? 'text-green-400' : 'text-blue-300'}>
                {ev.event}
              </span>
              {ev.data?.message && <span className="text-gray-400"> {ev.data.message}</span>}
              {ev.data?.progress_pct !== undefined && <span className="text-yellow-400"> ({ev.data.progress_pct}%)</span>}
            </div>
          ))}
        </div>
      )}

      {/* Document Preview */}
      {hasPreviewableContent && viewMode === 'preview' && (
        <DocumentPreview projectId={project.id} projectTitle={project.title} />
      )}

      {/* Figure Preview */}
      {hasPreviewableContent && viewMode === 'figures' && (
        <FigurePreview projectId={project.id} />
      )}

      {/* Artifact JSON view */}
      {viewMode === 'artifacts' && latestArtifact && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold mb-2 text-gray-600">Latest Artifact: {latestArtifact.artifact_type}</h3>
          <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded overflow-auto max-h-96">
            {JSON.stringify(latestArtifact.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
