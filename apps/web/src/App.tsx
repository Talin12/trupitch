import { BrowserRouter, Route, Routes } from "react-router-dom";
import CampaignBuilder from "./pages/CampaignBuilder";
import Dashboard from "./pages/Dashboard";
import Submit from "./pages/Submit";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Submit />} />
        <Route path="/admin" element={<Dashboard />} />
        <Route path="/admin/campaigns/new" element={<CampaignBuilder />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
