import React, { useEffect } from "react";
import { Outlet } from "react-router-dom";
import CookieConsent from "./components/CookieConsent.jsx";
import MaintenanceGate from "./components/MaintenanceGate.jsx";
import { startRenderKeepAlive } from "./utils/renderKeepAlive.js";

function App() {
  useEffect(() => startRenderKeepAlive(), []);

  return (
    <div style={{ height: "100%" }}>
      <MaintenanceGate>
        <Outlet />
      </MaintenanceGate>
      <CookieConsent />
    </div>
  );
}

export default App;
