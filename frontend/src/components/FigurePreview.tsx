import React, { useEffect, useState, useRef } from 'react';
import { Image, AlertCircle, Copy, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '../api/client';

interface Figure {
  figure_id: string;
  title: string;
  caption: string;
  diagram_type: string;
  mermaid: string;
  placement: string;
  supports_claim: string;
  venue_notes?: string;
}

interface FiguresData {
  figures: Figure[];
  total_figures: number;
  figure_plan: string;
  cross_references: Array<{ figure_id: string; section: string; reference_text: string }>;
  venue_compliance_notes: string;
}

interface FigurePreviewProps {
  projectId: string;
}

const DIAGRAM_TYPE_COLORS: Record<string, string> = {
  flowchart: 'bg-blue-100 text-blue-700',
  sequenceDiagram: 'bg-purple-100 text-purple-700',
  classDiagram: 'bg-indigo-100 text-indigo-700',
  'stateDiagram-v2': 'bg-amber-100 text-amber-700',
  'graph': 'bg-green-100 text-green-700',
  pie: 'bg-pink-100 text-pink-700',
  gantt: 'bg-orange-100 text-orange-700',
  'block-beta': 'bg-teal-100 text-teal-700',
};

export default function FigurePreview({ projectId }: FigurePreviewProps) {
  const [data, setData] = useState<FiguresData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getFigures(projectId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center justify-center gap-2 text-gray-500">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-raptor-600" />
          Loading figures...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <Image className="h-12 w-12 text-gray-300" />
          <p className="text-sm">No figures generated yet. The Visual Architect runs after the drafting stage.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image className="h-5 w-5 text-raptor-600" />
            <h3 className="font-semibold">Figures</h3>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-raptor-100 text-raptor-700">
              {data.total_figures} diagrams
            </span>
          </div>
        </div>
        {data.venue_compliance_notes && (
          <p className="text-xs text-gray-500 mt-2">{data.venue_compliance_notes}</p>
        )}
      </div>

      {/* Figures */}
      <div className="p-4 space-y-6">
        {data.figures.map((fig) => (
          <FigureCard key={fig.figure_id} figure={fig} />
        ))}
      </div>

      {/* Figure plan */}
      {data.figure_plan && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Figure Plan</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">{data.figure_plan}</p>
        </div>
      )}
    </div>
  );
}


function FigureCard({ figure }: { figure: Figure }) {
  const [showMermaid, setShowMermaid] = useState(false);
  const [copied, setCopied] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const typeColor = Object.entries(DIAGRAM_TYPE_COLORS).find(
    ([key]) => figure.diagram_type.startsWith(key) || figure.mermaid.startsWith(key)
  )?.[1] || 'bg-gray-100 text-gray-700';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(figure.mermaid);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Figure header */}
      <div className="bg-gray-50 dark:bg-gray-900 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-sm">{figure.title}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${typeColor}`}>
                {figure.diagram_type}
              </span>
              <span className="text-xs text-gray-400">{figure.placement}</span>
            </div>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 text-xs border rounded hover:bg-white dark:hover:bg-gray-800 transition-colors"
          >
            {copied ? <CheckCircle2 className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
            {copied ? 'Copied' : 'Copy Mermaid'}
          </button>
        </div>
      </div>

      {/* Mermaid diagram rendered via mermaid.ink */}
      <div className="p-4 bg-white dark:bg-gray-800 flex justify-center">
        <MermaidRenderer code={figure.mermaid} />
      </div>

      {/* Caption */}
      <div className="px-4 py-3 border-t border-gray-100 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400 italic">{figure.caption}</p>
        {figure.supports_claim && (
          <p className="text-xs text-raptor-600 mt-1">
            Supports: "{figure.supports_claim}"
          </p>
        )}
      </div>

      {/* Collapsible Mermaid source */}
      <div className="border-t border-gray-100 dark:border-gray-700">
        <button
          onClick={() => setShowMermaid(!showMermaid)}
          className="flex items-center gap-1 px-4 py-2 text-xs text-gray-500 hover:text-gray-700 w-full text-left"
        >
          {showMermaid ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          Mermaid Source
        </button>
        {showMermaid && (
          <pre className="px-4 pb-3 text-xs font-mono bg-gray-50 dark:bg-gray-900 overflow-x-auto whitespace-pre-wrap">
            {figure.mermaid}
          </pre>
        )}
      </div>
    </div>
  );
}


/** Renders Mermaid code as SVG using mermaid.ink (a free rendering service).
 *  Falls back to showing the source code if rendering fails. */
function MermaidRenderer({ code }: { code: string }) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    // Use mermaid.ink to render the diagram as SVG
    // UTF-8 safe base64 encoding (btoa only handles Latin1)
    const encoded = btoa(unescape(encodeURIComponent(code)));
    const url = `https://mermaid.ink/svg/${encoded}`;

    // Try to load as an image first
    const img = new window.Image();
    img.onload = () => setSvg(url);
    img.onerror = () => setError(true);
    img.src = url;

    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [code]);

  if (error) {
    // Fallback: render as styled code block
    return (
      <div className="w-full">
        <div className="flex items-center gap-2 text-xs text-amber-600 mb-2">
          <AlertCircle className="h-3 w-3" />
          Diagram preview unavailable. Mermaid source shown below.
        </div>
        <pre className="text-xs font-mono bg-gray-50 dark:bg-gray-900 p-3 rounded overflow-x-auto whitespace-pre-wrap border">
          {code}
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="flex items-center gap-2 text-gray-400 py-8">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-raptor-600" />
        <span className="text-xs">Rendering diagram...</span>
      </div>
    );
  }

  return (
    <img
      src={svg}
      alt="Mermaid diagram"
      className="max-w-full h-auto"
      style={{ maxHeight: '500px' }}
    />
  );
}
