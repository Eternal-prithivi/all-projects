import React from 'react';
import '../styles/animated-background.css';

const AnimatedBackground = () => (
  <div className="landing-backdrop" aria-hidden="true">
    <div className="landing-backdrop__beam" />
    <div className="landing-backdrop__grid" />
    <div className="landing-backdrop__orb landing-backdrop__orb--gold" />
    <div className="landing-backdrop__orb landing-backdrop__orb--warm" />
    <div className="landing-backdrop__stars" />
    <div className="landing-backdrop__vignette" />
  </div>
);

export default AnimatedBackground;
