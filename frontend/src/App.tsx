import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Topics from "./pages/Topics";
import Schemas from "./pages/Schemas";
import Connect from "./pages/Connect/index";
import Connections from "./pages/Connections/index";
import Policies from "./pages/Policies";
import Analysis from "./pages/Analysis";
import Settings from "./pages/Settings";
import History from "./pages/History";
import TeamAnalytics from "./pages/TeamAnalytics";

function App() {
  return (
    <>
      <Toaster position="top-right" richColors closeButton />
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
            <Route path="team-analytics" element={<TeamAnalytics />} />
            <Route path="history" element={<History />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
