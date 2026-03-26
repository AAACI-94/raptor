import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, Star, StarOff, Filter, BookOpen, FileText, BarChart3, DollarSign, Image, Tag, X, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

interface LibraryEntry {
  id: string;
  title: string;
  venue_profile_id: string | null;
  status: string;
  tags: string[];
  category: string | null;
  starred: boolean;
  abstract: string;
  word_count: number;
  figure_count: number;
  quality_score: number | null;
  total_cost_usd: number;
  revision_cycles: number;
  created_at: string;
  updated_at: string;
}

interface TagCount { tag: string; count: number; }

interface LibraryStats {
  total_projects: number;
  by_venue: Record<string, number>;
  by_status_group: Record<string, number>;
  avg_quality: number;
  total_cost: number;
  total_words: number;
  total_figures: number;
  top_tags: TagCount[];
}

const VENUE_LABELS: Record<string, string> = {
  sans_reading_room: 'SANS', ieee_sp: 'IEEE S&P', acm_ccs: 'ACM CCS',
  usenix_security: 'USENIX', acsac: 'ACSAC', dark_reading: 'Dark Reading',
  linkedin_article: 'LinkedIn', csa_research: 'CSA',
};

const STATUS_GROUPS: Record<string, { label: string; color: string }> = {
  in_progress: { label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  ready_to_publish: { label: 'Ready', color: 'bg-green-100 text-green-700' },
  published: { label: 'Published', color: 'bg-emerald-200 text-emerald-800' },
};

function qualityColor(score: number | null): string {
  if (!score) return 'bg-gray-200';
  if (score >= 8) return 'bg-green-500';
  if (score >= 6) return 'bg-yellow-500';
  return 'bg-red-400';
}

export default function Library() {
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [allTags, setAllTags] = useState<TagCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [venueFilter, setVenueFilter] = useState('');
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [starredOnly, setStarredOnly] = useState(false);
  const [sortBy, setSortBy] = useState('date');

  const fetchLibrary = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set('q', searchQuery);
      if (venueFilter) params.set('venue', venueFilter);
      if (tagFilter.length) params.set('tags', tagFilter.join(','));
      if (starredOnly) params.set('starred', 'true');
      params.set('sort', sortBy);

      const [results, tagData, statsData] = await Promise.all([
        fetch(`/api/projects/library/search?${params}`).then(r => r.json()),
        fetch('/api/projects/library/tags').then(r => r.json()),
        fetch('/api/projects/library/stats').then(r => r.json()),
      ]);
      setEntries(results);
      setAllTags(tagData);
      setStats(statsData);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, venueFilter, tagFilter, starredOnly, sortBy]);

  useEffect(() => { fetchLibrary(); }, [fetchLibrary]);

  const handleStar = async (id: string) => {
    await fetch(`/api/projects/${id}/star`, { method: 'PUT' });
    fetchLibrary();
  };

  const addTagFilter = (tag: string) => {
    if (!tagFilter.includes(tag)) setTagFilter([...tagFilter, tag]);
  };
  const removeTagFilter = (tag: string) => setTagFilter(tagFilter.filter(t => t !== tag));
  const clearFilters = () => { setSearchQuery(''); setVenueFilter(''); setTagFilter([]); setStarredOnly(false); };
  const hasActiveFilters = searchQuery || venueFilter || tagFilter.length || starredOnly;

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raptor-600" /></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><AlertCircle className="inline h-5 w-5 text-red-500 mr-2" />{error}</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Research Library</h1>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">Papers</div>
            <div className="text-xl font-bold">{stats.total_projects}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">Total Words</div>
            <div className="text-xl font-bold">{(stats.total_words / 1000).toFixed(0)}K</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">Figures</div>
            <div className="text-xl font-bold">{stats.total_figures}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">Avg Quality</div>
            <div className="text-xl font-bold">{stats.avg_quality.toFixed(1)}/10</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">Total Cost</div>
            <div className="text-xl font-bold">${stats.total_cost.toFixed(2)}</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-3">
            <div className="text-xs text-gray-500 uppercase">In Progress</div>
            <div className="text-xl font-bold">{stats.by_status_group?.in_progress || 0}</div>
          </div>
        </div>
      )}

      {/* Search + filters bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 mb-6 space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search papers by title, topic, or tags..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 text-sm"
            />
          </div>
          <select value={venueFilter} onChange={(e) => setVenueFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 text-sm">
            <option value="">All Venues</option>
            {Object.entries(VENUE_LABELS).map(([id, label]) => (
              <option key={id} value={id}>{label}</option>
            ))}
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 text-sm">
            <option value="date">Newest</option>
            <option value="quality">Quality</option>
            <option value="cost">Cost</option>
            <option value="title">Title</option>
            <option value="words">Length</option>
          </select>
          <button
            onClick={() => setStarredOnly(!starredOnly)}
            className={`px-3 py-2 border rounded-lg text-sm flex items-center gap-1 ${starredOnly ? 'bg-amber-50 border-amber-300 text-amber-700' : 'dark:bg-gray-700 dark:border-gray-600'}`}
          >
            <Star className="h-3.5 w-3.5" />{starredOnly ? 'Starred' : 'All'}
          </button>
        </div>

        {/* Active filters + tag cloud */}
        <div className="flex flex-wrap gap-2 items-center">
          {tagFilter.map(tag => (
            <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-raptor-100 text-raptor-700 rounded text-xs">
              {tag}<button onClick={() => removeTagFilter(tag)}><X className="h-3 w-3" /></button>
            </span>
          ))}
          {hasActiveFilters && (
            <button onClick={clearFilters} className="text-xs text-gray-500 hover:text-gray-700 underline">Clear all</button>
          )}
        </div>

        {/* Tag cloud */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {allTags.slice(0, 20).map(({ tag, count }) => (
              <button key={tag} onClick={() => addTagFilter(tag)}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  tagFilter.includes(tag) ? 'bg-raptor-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-raptor-50'
                }`}>
                {tag} <span className="opacity-60">({count})</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      {entries.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <BookOpen className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>{hasActiveFilters ? 'No papers match your filters.' : 'No papers yet. Create your first project to start building your library.'}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-raptor-300 transition-colors">
              <div className="flex items-start gap-4">
                {/* Star */}
                <button onClick={(e) => { e.preventDefault(); handleStar(entry.id); }}
                  className="mt-1 flex-shrink-0">
                  {entry.starred
                    ? <Star className="h-5 w-5 text-amber-500 fill-amber-500" />
                    : <StarOff className="h-5 w-5 text-gray-300 hover:text-amber-400" />
                  }
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <Link to={`/projects/${entry.id}`} className="hover:underline">
                    <h3 className="font-semibold text-lg truncate">{entry.title}</h3>
                  </Link>
                  {entry.abstract && (
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{entry.abstract}</p>
                  )}

                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {entry.venue_profile_id && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                        {VENUE_LABELS[entry.venue_profile_id] || entry.venue_profile_id}
                      </span>
                    )}
                    {entry.category && (
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                        {entry.category.replace(/_/g, ' ')}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      entry.status === 'PUBLISHED' ? 'bg-green-100 text-green-700' :
                      entry.status.includes('COMPLETE') || entry.status === 'REVIEW_PASSED' ? 'bg-emerald-100 text-emerald-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {entry.status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Tags */}
                  {entry.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {entry.tags.slice(0, 8).map(tag => (
                        <button key={tag} onClick={() => addTagFilter(tag)}
                          className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-500 hover:bg-raptor-50">
                          <Tag className="inline h-2.5 w-2.5 mr-0.5" />{tag}
                        </button>
                      ))}
                      {entry.tags.length > 8 && <span className="text-xs text-gray-400">+{entry.tags.length - 8}</span>}
                    </div>
                  )}
                </div>

                {/* Metrics */}
                <div className="flex-shrink-0 text-right space-y-1">
                  {entry.quality_score !== null && (
                    <div className="flex items-center gap-2 justify-end">
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div className={`h-2 rounded-full ${qualityColor(entry.quality_score)}`}
                          style={{ width: `${(entry.quality_score / 10) * 100}%` }} />
                      </div>
                      <span className="text-xs font-medium w-8">{entry.quality_score.toFixed(1)}</span>
                    </div>
                  )}
                  <div className="text-xs text-gray-400 flex items-center gap-1 justify-end">
                    <FileText className="h-3 w-3" />{entry.word_count > 0 ? `${(entry.word_count / 1000).toFixed(1)}K words` : 'No draft'}
                  </div>
                  {entry.figure_count > 0 && (
                    <div className="text-xs text-gray-400 flex items-center gap-1 justify-end">
                      <Image className="h-3 w-3" />{entry.figure_count} figures
                    </div>
                  )}
                  <div className="text-xs text-gray-400 flex items-center gap-1 justify-end">
                    <DollarSign className="h-3 w-3" />${entry.total_cost_usd.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-400">
                    {new Date(entry.updated_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
