import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Router } from "./app/Router";
import "./styles.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Application root is missing");
}

createRoot(root).render(
  <StrictMode>
    <Router />
  </StrictMode>
);
