
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/layout/Sidebar';
import Connections from './pages/Connections';
import GovernanceDashboard from './pages/governance/Dashboard';
import Policies from './pages/Policies';
import SchemaDetail from './pages/schemas/SchemaDetail';
import SchemaList from './pages/schemas/SchemaList';
import Topics from './pages/Topics';
import TopicDetail from './pages/TopicDetail';

import { Toaster } from 'sonner';

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/governance/dashboard" replace />} />
          <Route path="/governance/dashboard" element={<GovernanceDashboard />} />
          <Route path="/schemas" element={<SchemaList />} />
          <Route path="/schemas/:subject" element={<SchemaDetail />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/topics/:topicName" element={<TopicDetail />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/policies" element={<Policies />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
