import React, { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Workspace = lazy(() => import('./pages/Workspace'));
const Observatory = lazy(() => import('./pages/Observatory'));
const VenueManager = lazy(() => import('./pages/VenueManager'));
const About = lazy(() => import('./pages/About'));

function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-raptor-600" />
    </div>
  );
}

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/:projectId" element={<Workspace />} />
          <Route path="/observatory" element={<Observatory />} />
          <Route path="/observatory/:projectId" element={<Observatory />} />
          <Route path="/venues" element={<VenueManager />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
