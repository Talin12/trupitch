import { BrowserRouter, Route, Routes } from "react-router-dom";
import CampaignBuilder from "./pages/CampaignBuilder";
import Dashboard from "./pages/Dashboard";
import EventPage from "./pages/EventPage";
import Home from "./pages/Home";

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
