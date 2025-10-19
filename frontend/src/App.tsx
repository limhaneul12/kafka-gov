import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Topics from "./pages/Topics";
import Schemas from "./pages/Schemas";
import Connect from "./pages/Connect";
import Connections from "./pages/Connections";
import Policies from "./pages/Policies";
import Analysis from "./pages/Analysis";
import Settings from "./pages/Settings";

function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="topics" element={<Topics />} />
          <Route path="schemas" element={<Schemas />} />
          <Route path="connect" element={<Connect />} />
          <Route path="connections" element={<Connections />} />
          <Route path="policies" element={<Policies />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
