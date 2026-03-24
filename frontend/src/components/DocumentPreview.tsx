import React, { useEffect, useState } from 'react';
import { FileText, Download, Copy, CheckCircle2, AlertCircle, BookOpen, Hash, FileCheck } from 'lucide-react';
import { api } from '../api/client';

interface PreviewData {
  markdown: string;
  source: 'production' | 'draft' | 'partial';
  word_count: number;
  section_count?: number;
  reference_count?: number;
  checklist?: Array<{ item: string; status: string; detail?: string }>;
  formatting_notes?: string;
}

interface DocumentPreviewProps {
  projectId: string;
  projectTitle: string;
}

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  production: { label: 'Final Document', color: 'bg-green-100 text-green-700' },
  draft: { label: 'Draft Preview', color: 'bg-amber-100 text-amber-700' },
  partial: { label: 'Partial Preview', color: 'bg-blue-100 text-blue-700' },
};

export default function DocumentPreview({ projectId, projectTitle }: DocumentPreviewProps) {
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'checklist'>('preview');

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getPreview(projectId)
      .then(setPreview)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleCopyMarkdown = async () => {
    if (!preview) return;
    await navigator.clipboard.writeText(preview.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center justify-center gap-2 text-gray-500">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-raptor-600" />
          Loading preview...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex flex-col items-center gap-3 text-gray-500">
          <FileText className="h-12 w-12 text-gray-300" />
          <p className="text-sm">No document to preview yet. Complete more pipeline stages to see a preview.</p>
        </div>
      </div>
    );
  }

  if (!preview) return null;

  const sourceInfo = SOURCE_LABELS[preview.source] || SOURCE_LABELS.partial;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BookOpen className="h-5 w-5 text-raptor-600" />
            <h3 className="font-semibold">Document Preview</h3>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${sourceInfo.color}`}>
              {sourceInfo.label}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyMarkdown}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copied' : 'Copy Markdown'}
            </button>
            <a
              href={`/api/projects/${projectId}/export/docx`}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-raptor-600 text-white rounded-lg hover:bg-raptor-700 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Export DOCX
            </a>
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <Hash className="h-3 w-3" />
            {preview.word_count.toLocaleString()} words
          </span>
          {preview.section_count !== undefined && (
            <span className="flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {preview.section_count} sections
            </span>
          )}
          {preview.reference_count !== undefined && (
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              {preview.reference_count} references
            </span>
          )}
        </div>

        {/* Tabs (if checklist exists) */}
        {preview.checklist && preview.checklist.length > 0 && (
          <div className="flex gap-1 mt-3">
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1 text-xs rounded-md ${activeTab === 'preview' ? 'bg-raptor-100 text-raptor-700 dark:bg-raptor-900 dark:text-raptor-300' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Document
            </button>
            <button
              onClick={() => setActiveTab('checklist')}
              className={`px-3 py-1 text-xs rounded-md ${activeTab === 'checklist' ? 'bg-raptor-100 text-raptor-700 dark:bg-raptor-900 dark:text-raptor-300' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Checklist ({preview.checklist.length})
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      {activeTab === 'preview' ? (
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <MarkdownRenderer markdown={preview.markdown} />
        </div>
      ) : (
        <div className="p-4">
          <SubmissionChecklist checklist={preview.checklist || []} notes={preview.formatting_notes} />
        </div>
      )}
    </div>
  );
}


/** Simple markdown-to-HTML renderer (no external deps). */
function MarkdownRenderer({ markdown }: { markdown: string }) {
  const html = markdownToHtml(markdown);
  return (
    <article
      className="prose prose-gray dark:prose-invert max-w-none
        prose-headings:font-bold prose-headings:text-gray-900 dark:prose-headings:text-gray-100
        prose-h1:text-2xl prose-h1:border-b prose-h1:border-gray-200 prose-h1:pb-3 prose-h1:mb-4
        prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-3
        prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-2
        prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-p:leading-relaxed prose-p:mb-4
        prose-strong:text-gray-900 dark:prose-strong:text-gray-100
        prose-ul:my-3 prose-li:my-1
        prose-a:text-raptor-600 prose-a:no-underline hover:prose-a:underline"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/** Convert markdown to HTML without external libraries. */
function markdownToHtml(md: string): string {
  let html = md;

  // Escape HTML entities (except in our own generated tags)
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Headings (must come before bold since # lines shouldn't be bolded)
  html = html.replace(/^#{6}\s+(.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^#{5}\s+(.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-sm font-mono">$1</code>');

  // Unordered lists
  html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul class="list-disc pl-6">${match}</ul>`);

  // Numbered lists
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Blockquotes
  html = html.replace(/^&gt;\s+(.+)$/gm, '<blockquote class="border-l-4 border-gray-300 pl-4 italic text-gray-600 dark:text-gray-400 my-4">$1</blockquote>');

  // Horizontal rules
  html = html.replace(/^---+$/gm, '<hr class="my-6 border-gray-200 dark:border-gray-700" />');

  // Links (basic)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Citation markers like [1], [2] etc
  html = html.replace(/\[(\d+)\]/g, '<sup class="text-raptor-600 font-medium">[$1]</sup>');

  // Paragraphs: wrap text blocks not already in tags
  html = html.replace(/^(?!<[a-z])((?!^\s*$).+)$/gm, (match) => {
    // Don't wrap if it's already inside a tag or is a list item
    if (match.startsWith('<') || match.trim() === '') return match;
    return `<p>${match}</p>`;
  });

  // Clean up double line breaks
  html = html.replace(/\n{3,}/g, '\n\n');
  html = html.replace(/\n\n/g, '\n');

  return html;
}


function SubmissionChecklist({ checklist, notes }: { checklist: Array<{ item: string; status: string; detail?: string }>; notes?: string }) {
  const statusIcon = (status: string) => {
    if (status === 'pass') return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    if (status === 'warning') return <AlertCircle className="h-4 w-4 text-amber-500" />;
    return <AlertCircle className="h-4 w-4 text-red-500" />;
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {checklist.map((item, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900">
            {statusIcon(item.status)}
            <div className="flex-1">
              <div className="text-sm font-medium">{item.item}</div>
              {item.detail && <div className="text-xs text-gray-500 mt-0.5">{item.detail}</div>}
            </div>
          </div>
        ))}
      </div>
      {notes && (
        <div className="text-sm text-gray-500 border-t border-gray-200 dark:border-gray-700 pt-3">
          <strong>Notes:</strong> {notes}
        </div>
      )}
    </div>
  );
}
