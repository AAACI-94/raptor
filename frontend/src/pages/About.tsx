import React, { useState } from 'react';
import { BookOpen, Copy, Check, Shield, Search, Wrench, Sparkles, Scale, Brain } from 'lucide-react';
import { APP_VERSION, agents, selfHealingComponents, pipelineStages, publicationTargetTypes, techStack, qualityStandards, contextEngineering } from '../data/about';
import { changelog } from '../data/changelog';
import type { ChangelogItem } from '../data/changelog';

const BADGE_COLORS: Record<string, string> = {
  pipeline: 'bg-blue-100 text-blue-700',
  agents: 'bg-purple-100 text-purple-700',
  ui: 'bg-emerald-100 text-emerald-700',
  observatory: 'bg-amber-100 text-amber-700',
  healing: 'bg-red-100 text-red-700',
  api: 'bg-cyan-100 text-cyan-700',
  infra: 'bg-gray-100 text-gray-700',
  quality: 'bg-indigo-100 text-indigo-700',
  library: 'bg-teal-100 text-teal-700',
  context: 'bg-orange-100 text-orange-700',
};

const HEALING_ICONS: Record<string, typeof Shield> = { Shield, Search, Wrench };

export default function About() {
  const [copied, setCopied] = useState(false);

  const copyAsMarkdown = () => {
    const md = generateMarkdown();
    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3">
            <BookOpen className="h-8 w-8 text-raptor-500" />
            <h1 className="text-3xl font-bold">RAPTOR</h1>
            <span className="px-2 py-0.5 bg-raptor-100 text-raptor-700 rounded text-sm font-medium">v{APP_VERSION}</span>
          </div>
          <p className="text-gray-500 mt-2">Research Authoring Platform with Traceable Orchestrated Reasoning</p>
        </div>
        <button onClick={copyAsMarkdown}
          className="flex items-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50 text-sm">
          {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          {copied ? 'Copied' : 'Copy as Markdown'}
        </button>
      </div>

      {/* What is RAPTOR */}
      <section className="mb-8">
        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
          A Dockerized, local-first multi-agent authoring platform purpose-built for cybersecurity practitioners
          who need to transform domain expertise into published research artifacts. The system guides an author
          through a structured pipeline with seven domain-specialized agents, publication-adaptive quality models,
          journalistic verification standards, logical rigor enforcement, and full-stack observability.
        </p>
      </section>

      {/* Pipeline */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Pipeline</h2>
        <div className="space-y-2">
          {pipelineStages.map((stage, i) => (
            <div key={stage.name} className="flex items-start gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="w-7 h-7 rounded-full bg-raptor-100 text-raptor-700 flex items-center justify-center text-sm font-bold flex-shrink-0">{i + 1}</div>
              <div>
                <div className="font-semibold text-sm">{stage.name}</div>
                <div className="text-xs text-gray-500">{stage.description}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Agent Roster */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Agent Roster</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {agents.map((agent) => (
            <div key={agent.role} className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: agent.color }} />
                <span className="font-semibold text-sm">{agent.name}</span>
                <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">{agent.model}</span>
              </div>
              <p className="text-xs text-gray-500">{agent.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quality & Rigor Standards */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Scale className="h-5 w-5 text-indigo-500" />
          Quality &amp; Rigor Standards
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Every paper is evaluated against journalistic verification standards, logical rigor frameworks,
          and formal causal inference methods. These standards are enforced by both the Domain Writer (during drafting)
          and the Critical Reviewer (during evaluation).
        </p>
        <div className="space-y-4">
          {qualityStandards.map((standard) => (
            <div key={standard.name} className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-indigo-200 dark:border-indigo-900">
              <div className="font-semibold text-sm mb-2">{standard.name}</div>
              <ul className="space-y-1">
                {standard.items.map((item, i) => (
                  <li key={i} className="text-xs text-gray-500 flex items-start gap-2">
                    <span className="text-indigo-400 mt-0.5">-</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Context Engineering */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-orange-500" />
          Context Engineering
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Each agent receives the minimum context needed for its role. These optimizations reduce token cost,
          improve output quality, and enable cross-project learning.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {contextEngineering.map((ce) => (
            <div key={ce.name} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-orange-200 dark:border-orange-900">
              <div className="font-semibold text-sm mb-1">{ce.name}</div>
              <p className="text-xs text-gray-500">{ce.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Self-Healing System */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-red-500" />
          Self-Healing System
        </h2>
        <div className="grid gap-3 md:grid-cols-3">
          {selfHealingComponents.map((comp) => {
            const IconComponent = HEALING_ICONS[comp.icon] || Shield;
            return (
              <div key={comp.name} className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-900">
                <div className="flex items-center gap-2 mb-2">
                  <IconComponent className="h-4 w-4 text-red-500" />
                  <span className="font-semibold text-sm">{comp.name}</span>
                </div>
                <p className="text-xs text-gray-500">{comp.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Publication Targets */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Publication Targets</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {publicationTargetTypes.map((v) => (
            <div key={v.name} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="font-semibold text-sm">{v.name}</div>
              <div className="text-xs text-gray-400">e.g., {v.example}</div>
              <div className="text-xs text-gray-500 mt-1">{v.focus}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Tech Stack</h2>
        <div className="grid gap-2 md:grid-cols-2">
          {techStack.map((t) => (
            <div key={t.name} className="flex items-center gap-2 text-sm">
              <span className="text-gray-500 w-28">{t.name}:</span>
              <span className="font-mono text-xs">{t.tech}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Changelog */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Changelog</h2>
        <div className="space-y-6">
          {changelog.map((entry) => (
            <div key={entry.version} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-lg font-bold">v{entry.version}</span>
                <span className="text-xs text-gray-400">{entry.date}</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{entry.summary}</p>

              {entry.added && entry.added.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs font-semibold text-green-600 mb-1">Added</div>
                  {entry.added.map((item, i) => (
                    <ChangelogItemRow key={i} item={item} />
                  ))}
                </div>
              )}
              {entry.changed && entry.changed.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs font-semibold text-amber-600 mb-1">Changed</div>
                  {entry.changed.map((item, i) => (
                    <ChangelogItemRow key={i} item={item} />
                  ))}
                </div>
              )}
              {entry.fixed && entry.fixed.length > 0 && (
                <div>
                  <div className="text-xs font-semibold text-blue-600 mb-1">Fixed</div>
                  {entry.fixed.map((item, i) => (
                    <ChangelogItemRow key={i} item={item} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function ChangelogItemRow({ item }: { item: string | ChangelogItem }) {
  if (typeof item === 'string') {
    return <div className="text-xs text-gray-600 dark:text-gray-400 py-0.5 pl-3">- {item}</div>;
  }
  return (
    <div className="text-xs py-0.5 pl-3 flex items-start gap-2">
      {item.badge && (
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap ${BADGE_COLORS[item.badge] || 'bg-gray-100'}`}>
          {item.badge}
        </span>
      )}
      <div>
        <span className="font-medium">{item.title}</span>
        {item.description && <span className="text-gray-400 ml-1">: {item.description}</span>}
      </div>
    </div>
  );
}

function generateMarkdown(): string {
  const lines = [
    `# RAPTOR v${APP_VERSION}`,
    '',
    '## Research Authoring Platform with Traceable Orchestrated Reasoning',
    '',
    '### Pipeline',
    ...pipelineStages.map((s, i) => `${i + 1}. **${s.name}**: ${s.description}`),
    '',
    '### Agent Roster',
    ...agents.map(a => `- **${a.name}** (${a.model}): ${a.description}`),
    '',
    '### Quality & Rigor Standards',
    ...qualityStandards.flatMap(s => [`\n**${s.name}**`, ...s.items.map(i => `- ${i}`)]),
    '',
    '### Context Engineering',
    ...contextEngineering.map(c => `- **${c.name}**: ${c.description}`),
    '',
    '### Self-Healing System',
    ...selfHealingComponents.map(c => `- **${c.name}**: ${c.description}`),
    '',
    '### Publication Targets',
    ...publicationTargetTypes.map(v => `- **${v.name}** (${v.example}): ${v.focus}`),
    '',
    '### Tech Stack',
    ...techStack.map(t => `- **${t.name}**: ${t.tech}`),
    '',
    '### Changelog',
    ...changelog.flatMap(e => [
      `\n#### v${e.version} (${e.date})`,
      e.summary,
      ...(e.added || []).map(i => typeof i === 'string' ? `- Added: ${i}` : `- Added [${i.badge}]: ${i.title}`),
      ...(e.changed || []).map(i => typeof i === 'string' ? `- Changed: ${i}` : `- Changed [${i.badge}]: ${i.title}`),
      ...(e.fixed || []).map(i => typeof i === 'string' ? `- Fixed: ${i}` : `- Fixed [${i.badge}]: ${i.title}`),
    ]),
  ];
  return lines.join('\n');
}
