import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, PieChart, Pie, Cell } from 'recharts';
import { Activity, DollarSign, TrendingUp, Lightbulb, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { TraceSummary, QualityMetrics, CostSummary } from '../types';

const TABS = ['Traces', 'Quality', 'Cost', 'Improvement'] as const;
type Tab = typeof TABS[number];

const COLORS = ['#0c93e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'];

export default function Observatory() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<Tab>('Traces');
  const [traces, setTraces] = useState<TraceSummary | null>(null);
  const [quality, setQuality] = useState<QualityMetrics | null>(null);
  const [cost, setCost] = useState<CostSummary | null>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (projectId) {
          const [t, q, c] = await Promise.all([
            api.getTraces(projectId),
            api.getQuality(projectId),
            api.getCost(projectId),
          ]);
          setTraces(t); setQuality(q); setCost(c);
        } else {
          const [c, i] = await Promise.all([api.getCost(), api.getInsights()]);
          setCost(c); setInsights(i);
        }
      } catch (e: any) { setError(e.message); }
      setLoading(false);
    };
    load();
  }, [projectId]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raptor-600" /></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><AlertCircle className="inline h-5 w-5 text-red-500 mr-2" />{error}</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Observatory {projectId && `(Project)`}</h1>

      {/* Tab bar */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-raptor-600 text-raptor-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'Traces' && <TracesTab traces={traces} />}
      {tab === 'Quality' && <QualityTab quality={quality} />}
      {tab === 'Cost' && <CostTab cost={cost} />}
      {tab === 'Improvement' && <ImprovementTab insights={insights} />}
    </div>
  );
}

function TracesTab({ traces }: { traces: TraceSummary | null }) {
  if (!traces || traces.total_decisions === 0) {
    return <div className="text-center py-12 text-gray-500"><Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" /><p>No traces yet. Run a pipeline to generate decision traces.</p></div>;
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">{traces.total_decisions} decisions recorded</p>
      {Object.entries(traces.traces).map(([agent, entries]) => (
        <div key={agent} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="font-semibold text-sm mb-3 text-raptor-600">{agent.replace(/_/g, ' ')}</h3>
          <div className="space-y-2">
            {entries.map((e, i) => (
              <div key={i} className="text-xs border-l-2 border-gray-200 pl-3 py-1">
                <div className="font-medium">{e.decision}</div>
                {e.rationale && <div className="text-gray-500 mt-0.5">{e.rationale.slice(0, 200)}</div>}
                <div className="text-gray-400 mt-0.5">Confidence: {(e.confidence * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function QualityTab({ quality }: { quality: QualityMetrics | null }) {
  if (!quality || Object.keys(quality.dimensions).length === 0) {
    return <div className="text-center py-12 text-gray-500"><TrendingUp className="h-12 w-12 mx-auto mb-4 text-gray-300" /><p>No quality data yet.</p></div>;
  }

  const radarData = Object.entries(quality.dimensions).map(([dim, data]) => ({
    dimension: dim.replace(/_/g, ' '),
    score: data.avg_score,
    fullMark: 10,
  }));

  return (
    <div>
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="font-semibold mb-4">Quality Radar</h3>
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 10]} />
            <Radar name="Score" dataKey="score" stroke="#0c93e9" fill="#0c93e9" fillOpacity={0.3} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
        {Object.entries(quality.dimensions).map(([dim, data]) => (
          <div key={dim} className="bg-white dark:bg-gray-800 rounded-lg border p-4">
            <div className="text-xs font-medium text-gray-500 uppercase">{dim.replace(/_/g, ' ')}</div>
            <div className="text-2xl font-bold mt-1">{data.avg_score.toFixed(1)}</div>
            <div className="text-xs text-gray-400">Range: {data.min_score}-{data.max_score} ({data.evaluations} evals)</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CostTab({ cost }: { cost: CostSummary | null }) {
  if (!cost || cost.breakdown.length === 0) {
    return <div className="text-center py-12 text-gray-500"><DollarSign className="h-12 w-12 mx-auto mb-4 text-gray-300" /><p>No cost data yet.</p></div>;
  }

  const barData = cost.breakdown.map((b) => ({
    name: b.agent.replace(/_/g, ' ').slice(0, 12),
    cost: b.cost_usd,
    calls: b.calls,
  }));

  const pieData = cost.breakdown.map((b, i) => ({
    name: b.model.split('-').slice(1, 2).join(''),
    value: b.cost_usd,
    color: COLORS[i % COLORS.length],
  }));

  return (
    <div>
      {/* Totals */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg border p-4">
          <div className="text-xs text-gray-500 uppercase">Total Cost</div>
          <div className="text-2xl font-bold mt-1">${cost.totals.cost_usd.toFixed(2)}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border p-4">
          <div className="text-xs text-gray-500 uppercase">Input Tokens</div>
          <div className="text-2xl font-bold mt-1">{(cost.totals.input_tokens / 1000).toFixed(1)}K</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border p-4">
          <div className="text-xs text-gray-500 uppercase">Output Tokens</div>
          <div className="text-2xl font-bold mt-1">{(cost.totals.output_tokens / 1000).toFixed(1)}K</div>
        </div>
      </div>

      {/* Bar chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border p-6 mb-6">
        <h3 className="font-semibold mb-4">Cost by Agent</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="cost" fill="#0c93e9" name="Cost (USD)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Breakdown table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-4 py-2 text-left">Agent</th>
              <th className="px-4 py-2 text-left">Model</th>
              <th className="px-4 py-2 text-right">Calls</th>
              <th className="px-4 py-2 text-right">Input</th>
              <th className="px-4 py-2 text-right">Output</th>
              <th className="px-4 py-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {cost.breakdown.map((b, i) => (
              <tr key={i} className="border-t dark:border-gray-700">
                <td className="px-4 py-2">{b.agent.replace(/_/g, ' ')}</td>
                <td className="px-4 py-2 font-mono text-xs">{b.model}</td>
                <td className="px-4 py-2 text-right">{b.calls}</td>
                <td className="px-4 py-2 text-right">{(b.input_tokens / 1000).toFixed(1)}K</td>
                <td className="px-4 py-2 text-right">{(b.output_tokens / 1000).toFixed(1)}K</td>
                <td className="px-4 py-2 text-right font-medium">${b.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ImprovementTab({ insights }: { insights: any[] }) {
  if (insights.length === 0) {
    return <div className="text-center py-12 text-gray-500"><Lightbulb className="h-12 w-12 mx-auto mb-4 text-gray-300" /><p>No improvement insights yet. Submit author feedback to generate insights.</p></div>;
  }

  return (
    <div className="space-y-4">
      {insights.map((ins, i) => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-start gap-3">
            <Lightbulb className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="font-medium text-sm">{ins.dimension.replace(/_/g, ' ')}</div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{ins.insight}</p>
              <p className="text-sm text-raptor-600 mt-1 font-medium">{ins.recommendation}</p>
              <div className="text-xs text-gray-400 mt-2">
                Author avg: {ins.avg_author_rating} | System avg: {ins.avg_system_rating} | Based on {ins.feedback_count} ratings
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
