import { initThemeMode } from "flowbite-react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeInit } from "../.flowbite-react/init";
import { App } from "@/app/App";
import "@/index.css";

initThemeMode({ defaultMode: "light" });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeInit />
    <App />
  </StrictMode>,
);
