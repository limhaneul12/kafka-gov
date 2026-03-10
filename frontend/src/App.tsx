import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'sonner';
import Layout from './components/layout/Sidebar';
import Connections from './pages/Connections/index';
import ConsumerDetail from './pages/ConsumerDetail';
import Consumers from './pages/Consumers';
import GovernanceDashboard from './pages/governance/Dashboard';
import History from './pages/History';
import Policies from './pages/Policies';
import SchemaPolicies from './pages/SchemaPolicies';
import SchemaDetail from './pages/schemas/SchemaDetail';
import SchemaList from './pages/schemas/SchemaList';
import TopicDetail from './pages/TopicDetail';
import Topics from './pages/Topics';

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/governance/dashboard" replace />} />
          <Route path="/governance/dashboard" element={<GovernanceDashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/schemas" element={<SchemaList />} />
          <Route path="/schemas/:subject" element={<SchemaDetail />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/topics/:topicName" element={<TopicDetail />} />
          <Route path="/consumers" element={<Consumers />} />
          <Route path="/consumers/:groupId" element={<ConsumerDetail />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/schemas/policies" element={<SchemaPolicies />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
