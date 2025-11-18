import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Topics from "./pages/Topics";
import TopicDetail from "./pages/TopicDetail";
import TopicPolicies from "./pages/TopicPolicies";
import Schemas from "./pages/Schemas";
import SchemaPolicies from "./pages/SchemaPolicies";
import IncidentPolicies from "./pages/IncidentPolicies";
import IncidentPolicyComposer from "./pages/IncidentPolicyComposer";
import Consumers from "./pages/Consumers";
import ConsumerDetail from "./pages/ConsumerDetail";
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
            <Route path="topics/:topicName" element={<TopicDetail />} />
            <Route path="topics/policies" element={<TopicPolicies />} />
            <Route path="schemas" element={<Schemas />} />
            <Route path="schemas/policies" element={<SchemaPolicies />} />
            <Route path="policies/incidents" element={<IncidentPolicies />} />
            <Route path="policies/incidents/:policyId" element={<IncidentPolicyComposer />} />
            <Route path="consumers" element={<Consumers />} />
            <Route path="consumers/:groupId" element={<ConsumerDetail />} />
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
