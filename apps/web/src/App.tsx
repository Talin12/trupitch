import { BrowserRouter, Route, Routes } from "react-router-dom";
import CampaignBuilder from "./pages/CampaignBuilder";
import Dashboard from "./pages/Dashboard";
import EventPage from "./pages/EventPage";
import Home from "./pages/Home";

// All client-side routes for the whole SPA. There are two audiences:
//   Hacker-facing:   "/" (event list) -> "/events/:id" (event details,
//                    GitHub auth, submission form + live progress)
//   Organizer-facing: "/admin" (leaderboard dashboard) and
//                    "/admin/campaigns/new" (campaign builder)
// There is currently no route guard on the /admin paths — anyone with
// the URL can reach them, since organizer authentication doesn't exist
// yet (see docs/PRD.md's Non-Goals).
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/events/:id" element={<EventPage />} />
        <Route path="/admin" element={<Dashboard />} />
        <Route path="/admin/campaigns/new" element={<CampaignBuilder />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
