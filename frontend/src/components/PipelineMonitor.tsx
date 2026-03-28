import React, { useMemo } from 'react';
import { CheckCircle2, Loader2, Clock, AlertTriangle, RotateCcw } from 'lucide-react';
import type { PipelineEvent } from '../types';

interface StageInfo {
  key: string;
  label: string;
  agent: string;
  description: string;
  estimatedSeconds: number;
}

const PIPELINE_STAGES: StageInfo[] = [
  { key: 'research', label: 'Research', agent: 'Research Strategist', description: 'Building research plan with grounded sources', estimatedSeconds: 100 },
  { key: 'structure', label: 'Structure', agent: 'Structure Architect', description: 'Generating publication-appropriate outline', estimatedSeconds: 90 },
  { key: 'draft', label: 'Drafting', agent: 'Domain Writer', description: 'Writing each section with Toulmin arguments', estimatedSeconds: 200 },
  { key: 'figures', label: 'Figures', agent: 'Visual Architect', description: 'Creating professional diagrams', estimatedSeconds: 150 },
  { key: 'review', label: 'Review', agent: 'Critical Reviewer', description: 'Evaluating against quality rubric', estimatedSeconds: 120 },
  { key: 'production', label: 'Production', agent: 'Production Agent', description: 'Formatting document and bibliography', estimatedSeconds: 40 },
];

type StageStatus = 'pending' | 'active' | 'completed' | 'revision';

interface PipelineMonitorProps {
  projectStatus: string;
  events: PipelineEvent[];
  revisionCycles: number;
  maxRevisions: number;
}

export default function PipelineMonitor({ projectStatus, events, revisionCycles, maxRevisions }: PipelineMonitorProps) {
  // Derive stage statuses from project status and events
  const stageStatuses = useMemo(() => {
    const statuses: Record<string, StageStatus> = {};
    const statusUpper = projectStatus.toUpperCase();

    // Map project status to stage statuses
    const stageOrder = ['research', 'structure', 'draft', 'figures', 'review', 'production'];
    let activeFound = false;

    for (const stage of stageOrder) {
      const stageUpper = stage === 'draft' ? 'DRAFT' : stage === 'figures' ? 'ILLUSTRAT' : stage.toUpperCase();

      if (statusUpper.includes(stageUpper + 'ING') || statusUpper.includes(stageUpper + 'TING')) {
        statuses[stage] = 'active';
        activeFound = true;
      } else if (!activeFound && (
        statusUpper.includes(stageUpper.slice(0, 5) + '_COMPLETE') ||
        statusUpper === 'REVIEW_PASSED' && stage !== 'production' ||
        statusUpper === 'PRODUCTION_COMPLETE' ||
        statusUpper === 'PUBLISHED'
      )) {
        statuses[stage] = 'completed';
      } else if (statusUpper === 'REVISION_REQUESTED' && (stage === 'draft' || stage === 'figures')) {
        statuses[stage] = 'revision';
        activeFound = true;
      } else if (activeFound) {
        statuses[stage] = 'pending';
      } else {
        statuses[stage] = 'completed';
      }
    }

    // Special cases
    if (statusUpper === 'TOPIC_SELECTED') {
      stageOrder.forEach(s => statuses[s] = 'pending');
    }
    if (statusUpper === 'PUBLISHED' || statusUpper === 'PRODUCTION_COMPLETE') {
      stageOrder.forEach(s => statuses[s] = 'completed');
    }

    return statuses;
  }, [projectStatus]);

  // Get latest progress message per agent from events
  const latestProgress = useMemo(() => {
    const progress: Record<string, { message: string; pct: number }> = {};
    for (const ev of events) {
      if (ev.event === 'agent_progress' && ev.agent && ev.data) {
        progress[ev.agent] = {
          message: ev.data.message || '',
          pct: ev.data.progress_pct || 0,
        };
      }
      if (ev.event === 'agent_completed' && ev.agent) {
        progress[ev.agent] = { message: 'Complete', pct: 100 };
      }
    }
    return progress;
  }, [events]);

  // Dynamic time estimates from backend (overrides hardcoded defaults)
  const dynamicEstimates = useMemo(() => {
    const overrides: Record<string, number> = {};
    for (const ev of events) {
      if (ev.event === 'agent_progress' && ev.agent === 'domain_writer' && ev.data?.estimated_seconds) {
        overrides['draft'] = ev.data.estimated_seconds;
      }
    }
    return overrides;
  }, [events]);

  // Compute stage durations from events
  const stageDurations = useMemo(() => {
    const durations: Record<string, number> = {};
    const starts: Record<string, number> = {};

    for (const ev of events) {
      if (ev.event === 'agent_started' && ev.agent) {
        starts[ev.agent] = Date.now(); // Approximate; events don't carry timestamps
      }
      if (ev.event === 'agent_completed' && ev.agent && starts[ev.agent]) {
        durations[ev.agent] = Math.round((Date.now() - starts[ev.agent]) / 1000);
      }
    }
    return durations;
  }, [events]);

  // Overall progress
  const completedCount = Object.values(stageStatuses).filter(s => s === 'completed').length;
  const totalStages = PIPELINE_STAGES.length;
  const overallPct = Math.round((completedCount / totalStages) * 100);

  // ETA calculation
  const remainingStages = PIPELINE_STAGES.filter(s => stageStatuses[s.key] === 'pending' || stageStatuses[s.key] === 'active');
  const activeStage = PIPELINE_STAGES.find(s => stageStatuses[s.key] === 'active');
  const activeAgentKey = activeStage?.key;
  const activeAgentProgress = activeAgentKey ? latestProgress[
    activeStage.agent === 'Research Strategist' ? 'research_strategist' :
    activeStage.agent === 'Structure Architect' ? 'structure_architect' :
    activeStage.agent === 'Domain Writer' ? 'domain_writer' :
    activeStage.agent === 'Visual Architect' ? 'visual_architect' :
    activeStage.agent === 'Critical Reviewer' ? 'critical_reviewer' :
    activeStage.agent === 'Production Agent' ? 'production_agent' : ''
  ] : undefined;

  const etaSeconds = remainingStages.reduce((sum, s) => {
    const estimate = dynamicEstimates[s.key] ?? s.estimatedSeconds;
    if (stageStatuses[s.key] === 'active' && activeAgentProgress) {
      // Partial: estimate remaining based on progress percentage
      const remaining = estimate * (1 - activeAgentProgress.pct / 100);
      return sum + remaining;
    }
    return sum + estimate;
  }, 0);

  const isRunning = Object.values(stageStatuses).some(s => s === 'active');
  const isDone = projectStatus === 'PRODUCTION_COMPLETE' || projectStatus === 'PUBLISHED';

  if (projectStatus === 'TOPIC_SELECTED') {
    return null; // Don't show monitor before pipeline starts
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
      {/* Header with overall progress */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold">Pipeline Monitor</h3>
          {isRunning && (
            <span className="flex items-center gap-1.5 text-xs text-raptor-600 bg-raptor-50 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-raptor-500 animate-pulse" />
              Running
            </span>
          )}
          {isDone && (
            <span className="flex items-center gap-1.5 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="h-3 w-3" />
              Complete
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500">
          {isRunning && etaSeconds > 0 && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              ~{Math.ceil(etaSeconds / 60)} min remaining
            </span>
          )}
          {isDone && <span>All stages complete</span>}
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2 mb-4">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${isDone ? 'bg-green-500' : 'bg-raptor-500'}`}
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Revision warning */}
      {revisionCycles > 0 && (
        <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-3 py-1.5 rounded mb-3">
          <RotateCcw className="h-3 w-3" />
          Revision cycle {revisionCycles}/{maxRevisions}: Reviewer requested changes, re-drafting
        </div>
      )}

      {/* Stage-by-stage breakdown */}
      <div className="space-y-1">
        {PIPELINE_STAGES.map((stage) => {
          const status = stageStatuses[stage.key] || 'pending';
          const agentKey = stage.agent.toLowerCase().replace(/ /g, '_');
          const progress = latestProgress[agentKey];
          const duration = stageDurations[agentKey];

          return (
            <div
              key={stage.key}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                status === 'active' ? 'bg-raptor-50 dark:bg-raptor-950 border border-raptor-200 dark:border-raptor-800' :
                status === 'completed' ? 'bg-gray-50 dark:bg-gray-750' :
                status === 'revision' ? 'bg-amber-50 dark:bg-amber-950 border border-amber-200' :
                ''
              }`}
            >
              {/* Status icon */}
              <div className="w-5 flex-shrink-0">
                {status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                {status === 'active' && <Loader2 className="h-4 w-4 text-raptor-500 animate-spin" />}
                {status === 'revision' && <AlertTriangle className="h-4 w-4 text-amber-500" />}
                {status === 'pending' && <div className="h-4 w-4 rounded-full border-2 border-gray-300 dark:border-gray-600" />}
              </div>

              {/* Stage info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-medium ${status === 'active' ? 'text-raptor-700 dark:text-raptor-300' : status === 'completed' ? 'text-gray-600' : 'text-gray-400'}`}>
                    {stage.label}
                  </span>
                  <span className="text-xs text-gray-400">{stage.agent}</span>
                </div>

                {/* Active stage: show what it's doing */}
                {status === 'active' && progress && (
                  <div className="mt-1">
                    <div className="text-xs text-raptor-600 dark:text-raptor-400">{progress.message}</div>
                    {progress.pct > 0 && (
                      <div className="w-full bg-raptor-100 dark:bg-raptor-900 rounded-full h-1 mt-1">
                        <div className="bg-raptor-500 rounded-full h-1 transition-all duration-300" style={{ width: `${progress.pct}%` }} />
                      </div>
                    )}
                  </div>
                )}

                {/* Completed stage: show what it produced */}
                {status === 'completed' && (
                  <div className="text-xs text-gray-400 mt-0.5">{stage.description}</div>
                )}

                {/* Revision stage */}
                {status === 'revision' && (
                  <div className="text-xs text-amber-600 mt-0.5">Re-running: Reviewer requested changes</div>
                )}
              </div>

              {/* Duration / ETA */}
              <div className="text-xs text-gray-400 flex-shrink-0 w-16 text-right">
                {status === 'completed' && duration && `${duration}s`}
                {status === 'active' && `~${Math.ceil((dynamicEstimates[stage.key] ?? stage.estimatedSeconds) / 60)}m`}
                {status === 'pending' && `~${Math.ceil((dynamicEstimates[stage.key] ?? stage.estimatedSeconds) / 60)}m`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
