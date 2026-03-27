import React, { useEffect, useState } from 'react';
import { Building2, ChevronRight, AlertCircle } from 'lucide-react';
import { api } from '../api/client';
import type { VenueProfile } from '../types';

const PUBLICATION_TYPE_LABELS: Record<string, string> = {
  practitioner_repository: 'Practitioner',
  academic_conference: 'Academic',
  industry_publication: 'Industry',
  self_published: 'Self-Published',
  custom: 'Custom',
};

const PUBLICATION_TYPE_COLORS: Record<string, string> = {
  practitioner_repository: 'bg-blue-100 text-blue-700',
  academic_conference: 'bg-purple-100 text-purple-700',
  industry_publication: 'bg-amber-100 text-amber-700',
  self_published: 'bg-green-100 text-green-700',
  custom: 'bg-gray-100 text-gray-700',
};

export default function PublicationManager() {
  const [publications, setPublications] = useState<VenueProfile[]>([]);
  const [selected, setSelected] = useState<VenueProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listVenues()
      .then(setPublications)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raptor-600" /></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><AlertCircle className="inline h-5 w-5 text-red-500 mr-2" />{error}</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Publication Targets</h1>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Publication target list */}
        <div className="space-y-2">
          {publications.map((v) => (
            <button key={v.id} onClick={() => setSelected(v)}
              className={`w-full text-left p-4 rounded-lg border transition-colors ${
                selected?.id === v.id
                  ? 'border-raptor-400 bg-raptor-50 dark:bg-raptor-950'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-raptor-200'
              }`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{v.display_name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${PUBLICATION_TYPE_COLORS[v.venue_type] || 'bg-gray-100'}`}>
                      {PUBLICATION_TYPE_LABELS[v.venue_type] || v.venue_type}
                    </span>
                    {v.is_custom && <span className="text-xs text-gray-400">Custom</span>}
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-400" />
              </div>
            </button>
          ))}
        </div>

        {/* Publication target detail */}
        {selected && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
            <div>
              <h2 className="text-xl font-bold">{selected.display_name}</h2>
              <p className="text-sm text-gray-500 mt-1">{selected.description}</p>
            </div>

            {/* Quality Rubric */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Quality Rubric</h3>
              <div className="space-y-2">
                {selected.profile_data.quality_rubric.dimensions.map((d) => (
                  <div key={d.name} className="flex items-center gap-3">
                    <div className="w-32 text-sm">{d.name.replace(/_/g, ' ')}</div>
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-3 relative">
                      <div className="bg-raptor-500 rounded-full h-3" style={{ width: `${d.weight * 100}%` }} />
                    </div>
                    <div className="text-xs text-gray-500 w-12 text-right">{(d.weight * 100).toFixed(0)}%</div>
                    <div className="text-xs text-gray-400 w-16">min: {d.min_passing}</div>
                  </div>
                ))}
              </div>
              <div className="text-xs text-gray-400 mt-2">
                Passing threshold: {selected.profile_data.quality_rubric.passing_threshold}/10
              </div>
            </div>

            {/* Tone Profile */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Tone Profile</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">Register:</span> {selected.profile_data.tone_profile.register}</div>
                <div><span className="text-gray-500">Person:</span> {selected.profile_data.tone_profile.person}</div>
                <div><span className="text-gray-500">Voice:</span> {selected.profile_data.tone_profile.voice}</div>
                <div><span className="text-gray-500">Jargon:</span> {selected.profile_data.tone_profile.jargon_level}</div>
              </div>
            </div>

            {/* Citation Format */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Citation Format</h3>
              <div className="text-sm">
                <div><span className="text-gray-500">Style:</span> {selected.profile_data.citation_format.style}</div>
                <div><span className="text-gray-500">Min references:</span> {selected.profile_data.citation_format.minimum_references}</div>
              </div>
            </div>

            {/* Structure Template */}
            <div>
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Required Sections</h3>
              <div className="space-y-1">
                {selected.profile_data.structural_template.required_sections.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-sm py-1 border-b border-gray-100 dark:border-gray-700">
                    <span>{s.name}</span>
                    <span className="text-xs text-gray-400">
                      {s.min_words && s.max_words ? `${s.min_words}-${s.max_words} words` : 'No limit'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Reviewer Persona */}
            {selected.profile_data.review_simulation_persona?.description && (
              <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Reviewer Persona</h3>
                <p className="text-sm italic text-gray-600 dark:text-gray-400">
                  "{selected.profile_data.review_simulation_persona.description}"
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
