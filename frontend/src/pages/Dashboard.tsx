import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, FileText, Clock, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { ProjectSummary, VenueProfile } from '../types';

const STATUS_COLORS: Record<string, string> = {
  TOPIC_SELECTED: 'bg-gray-200 text-gray-700',
  RESEARCHING: 'bg-blue-100 text-blue-700',
  RESEARCH_COMPLETE: 'bg-blue-200 text-blue-800',
  STRUCTURING: 'bg-indigo-100 text-indigo-700',
  STRUCTURE_COMPLETE: 'bg-indigo-200 text-indigo-800',
  DRAFTING: 'bg-purple-100 text-purple-700',
  DRAFT_COMPLETE: 'bg-purple-200 text-purple-800',
  REVIEWING: 'bg-amber-100 text-amber-700',
  REVISION_REQUESTED: 'bg-red-100 text-red-700',
  REVIEW_PASSED: 'bg-green-100 text-green-700',
  PRODUCING: 'bg-emerald-100 text-emerald-700',
  PRODUCTION_COMPLETE: 'bg-emerald-200 text-emerald-800',
  PUBLISHED: 'bg-green-200 text-green-800',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [venues, setVenues] = useState<VenueProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newTopic, setNewTopic] = useState('');
  const [newVenue, setNewVenue] = useState('');
  const [newContext, setNewContext] = useState('');

  useEffect(() => {
    Promise.all([api.listProjects(), api.listVenues()])
      .then(([p, v]) => { setProjects(p); setVenues(v); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      const project = await api.createProject({
        title: newTitle,
        topic_description: newTopic,
        author_context: newContext,
        venue_profile_id: newVenue || null,
      });
      navigate(`/projects/${project.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raptor-600" /></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-2"><AlertCircle className="h-5 w-5 text-red-500" /><span className="text-red-700">{error}</span></div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Research Projects</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-raptor-600 text-white rounded-lg hover:bg-raptor-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Project
        </button>
      </div>

      {showCreate && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6 space-y-4">
          <h2 className="text-lg font-semibold">Create New Project</h2>
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <input type="text" value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="Paper title" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Topic Description</label>
            <textarea value={newTopic} onChange={(e) => setNewTopic(e.target.value)} rows={3}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="Describe your research topic..." />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Target Venue</label>
            <select value={newVenue} onChange={(e) => setNewVenue(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600">
              <option value="">Select a venue...</option>
              {venues.map((v) => <option key={v.id} value={v.id}>{v.display_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Author Context (optional)</label>
            <textarea value={newContext} onChange={(e) => setNewContext(e.target.value)} rows={2}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600" placeholder="Prior work, key ideas, constraints..." />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate}
              className="px-4 py-2 bg-raptor-600 text-white rounded-lg hover:bg-raptor-700">Create</button>
            <button onClick={() => setShowCreate(false)}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No projects yet. Create your first research project to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-raptor-300 transition-colors">
              <h3 className="font-semibold text-lg mb-2">{p.title}</h3>
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[p.status] || 'bg-gray-100'}`}>
                  {p.status.replace(/_/g, ' ')}
                </span>
                {p.revision_cycles > 0 && (
                  <span className="text-xs text-amber-600">Rev {p.revision_cycles}</span>
                )}
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="h-3 w-3" />
                {new Date(p.updated_at).toLocaleDateString()}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
