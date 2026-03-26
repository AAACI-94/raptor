import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Library, LayoutDashboard, BarChart3, Building2, Info, Plus } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Library', icon: Library },
  { path: '/new', label: 'New Project', icon: Plus },
  { path: '/observatory', label: 'Observatory', icon: BarChart3 },
  { path: '/venues', label: 'Venues', icon: Building2 },
  { path: '/about', label: 'About', icon: Info },
];

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-gray-100 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <Link to="/" className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-raptor-400" />
            <span className="text-lg font-bold">RAPTOR</span>
          </Link>
          <p className="text-xs text-gray-400 mt-1">Research Authoring Platform</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-raptor-700 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
          RAPTOR v1.0.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
