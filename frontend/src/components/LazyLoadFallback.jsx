import React from "react";
import "../styles/lazy-load-fallback.css";

const LazyLoadFallback = () => {
  return (
    <div className="lazy-load-container">
      <div className="lazy-load-spinner">
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
      </div>
      <p className="lazy-load-text">Loading...</p>
    </div>
  );
};

export default LazyLoadFallback;
