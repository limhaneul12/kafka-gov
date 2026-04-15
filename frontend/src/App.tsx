import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'sonner';

import Layout from './components/layout/Sidebar';
import Connections from './pages/Connections/index';
import SchemaPolicies from './pages/SchemaPolicies';
import SchemaDetail from './pages/schemas/SchemaDetail';
import SchemaList from './pages/schemas/SchemaList';

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/schemas" replace />} />
          <Route path="/schemas" element={<SchemaList />} />
          <Route path="/schemas/:subject" element={<SchemaDetail />} />
          <Route path="/schemas/policies" element={<SchemaPolicies />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="*" element={<Navigate to="/schemas" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
