import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import CampaignBuilder from "./pages/CampaignBuilder";
import Dashboard from "./pages/Dashboard";
import EventPage from "./pages/EventPage";
import Home from "./pages/Home";
import OrganizerLogin from "./pages/OrganizerLogin";
import { getOrganizerToken } from "./lib/auth";

function RequireOrganizer({ children }: { children: React.ReactElement }) {
  return getOrganizerToken() ? children : <Navigate to="/admin/login" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/events/:id" element={<EventPage />} />
        <Route path="/admin/login" element={<OrganizerLogin />} />
        <Route
          path="/admin"
          element={
            <RequireOrganizer>
              <Dashboard />
            </RequireOrganizer>
          }
        />
        <Route
          path="/admin/campaigns/new"
          element={
            <RequireOrganizer>
              <CampaignBuilder />
            </RequireOrganizer>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
