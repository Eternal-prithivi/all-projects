import React, { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import CookieConsent from "./components/CookieConsent.jsx";
import MaintenanceGate from "./components/MaintenanceGate.jsx";
import { startRenderKeepAlive } from "./utils/renderKeepAlive.js";

function App() {
  useEffect(() => startRenderKeepAlive(), []);

  return (
    <div className="app-root">
      <MaintenanceGate>
        <Outlet />
      </MaintenanceGate>
      <CookieConsent />
      <ToastContainer
        position="top-right"
        autoClose={4000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        pauseOnFocusLoss={false}
        draggable={false}
        pauseOnHover
        theme="dark"
        limit={4}
        style={{ zIndex: 99999 }}
      />
    </div>
  );
}

export default App;
