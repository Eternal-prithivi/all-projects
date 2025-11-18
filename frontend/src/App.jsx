import React from "react";
import { Outlet } from "react-router-dom";

function App() {
  // Use a style prop to ensure the app container fills its parent
  return (
    <div style={{ height: "100%" }}>
      <Outlet />
    </div>
  );
}

export default App;
