import { jsx as _jsx } from "react/jsx-runtime";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { AuthProvider } from "../shared/auth/AuthContext";
import "../index.css";
const rootElement = document.getElementById("root");
if (!rootElement) {
    throw new Error("Elemento #root não encontrado em index.html");
}
createRoot(rootElement).render(_jsx(StrictMode, { children: _jsx(AuthProvider, { children: _jsx(App, {}) }) }));
