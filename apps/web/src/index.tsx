import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
// Global dark-theme body styles (bg-zinc-950/text-zinc-50) — imported
// once here so every page inherits it without needing to set its own
// background.
import "./index.css";

// Standard Vite/React 18 mount point: renders <App /> (which owns all
// routing) into the <div id="root"> in index.html.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
