import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Library, BarChart3, Building2, Info, Plus } from 'lucide-react';
import { api } from '../api/client';

const NAV_ITEMS = [
  { path: '/', label: 'Library', icon: Library },
  { path: '/new', label: 'New Project', icon: Plus },
  { path: '/observatory', label: 'Observatory', icon: BarChart3 },
  { path: '/publications', label: 'Publications', icon: Building2 },
  { path: '/about', label: 'About', icon: Info },
];

const PAGE_TITLES: Record<string, string> = {
  '/': 'Library',
  '/new': 'New Project',
  '/observatory': 'Observatory',
  '/publications': 'Publication Targets',
  '/about': 'About',
};

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const [version, setVersion] = useState('');

  // Fetch version from backend health endpoint (single source of truth: pyproject.toml)
  useEffect(() => {
    api.health()
      .then((data) => setVersion(data.version || ''))
      .catch(() => setVersion(''));
  }, []);

  // Set page title based on route
  useEffect(() => {
    const base = 'RAPTOR';
    const pageTitle = PAGE_TITLES[location.pathname] ||
      (location.pathname.startsWith('/projects/') ? 'Workspace' :
       location.pathname.startsWith('/observatory/') ? 'Observatory' : '');
    document.title = pageTitle ? `${pageTitle} | ${base}` : base;
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex">
      {/* Skip navigation for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-raptor-600 focus:text-white focus:rounded-lg"
      >
        Skip to main content
      </a>

      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-gray-100 flex flex-col" aria-label="Main navigation">
        <div className="p-4 border-b border-gray-700">
          <Link to="/" className="flex items-center gap-2" aria-label="RAPTOR home">
            <BookOpen className="h-6 w-6 text-raptor-400" aria-hidden="true" />
            <span className="text-lg font-bold">RAPTOR</span>
          </Link>
          <p className="text-xs text-gray-400 mt-1">Research Authoring Platform</p>
        </div>

        <nav className="flex-1 p-4 space-y-1" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={isActive ? 'page' : undefined}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-raptor-400 ${
                  isActive
                    ? 'bg-raptor-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-700 text-xs text-gray-500" aria-label="Application version">
          {version ? `RAPTOR v${version}` : 'RAPTOR'}
        </div>
      </aside>

      {/* Main content */}
      <main id="main-content" className="flex-1 overflow-auto" role="main">
        <div className="max-w-7xl mx-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
