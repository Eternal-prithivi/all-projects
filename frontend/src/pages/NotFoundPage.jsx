import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import '../styles/error-pages.css';

const NotFoundPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const canvasRef = useRef(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [glitchText, setGlitchText] = useState('404');
  const [searchQuery, setSearchQuery] = useState('');

  // Particle starfield animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Create particles
    const particles = Array.from({ length: 80 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedX: (Math.random() - 0.5) * 0.3,
      speedY: (Math.random() - 0.5) * 0.3,
      opacity: Math.random() * 0.6 + 0.2,
      pulse: Math.random() * Math.PI * 2,
    }));

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(p => {
        p.x += p.speedX;
        p.y += p.speedY;
        p.pulse += 0.02;
        
        // Wrap around
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        
        const alpha = p.opacity * (0.5 + 0.5 * Math.sin(p.pulse));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 215, 0, ${alpha})`;
        ctx.fill();
      });

      // Draw connecting lines between close particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(255, 215, 0, ${0.05 * (1 - dist / 100)})`;
            ctx.stroke();
          }
        }
      }
      
      animationId = requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  // Glitch text effect
  useEffect(() => {
    const chars = '!@#$%^&*()_+-=[]{}|;:,.<>?01';
    let interval;
    
    const glitch = () => {
      const original = '404';
      let result = '';
      for (let i = 0; i < original.length; i++) {
        result += Math.random() < 0.3 ? chars[Math.floor(Math.random() * chars.length)] : original[i];
      }
      setGlitchText(result);
      setTimeout(() => setGlitchText('404'), 100);
    };

    interval = setInterval(glitch, 3000);
    return () => clearInterval(interval);
  }, []);

  // Mouse parallax
  const handleMouseMove = (e) => {
    const { clientX, clientY } = e;
    const x = (clientX / window.innerWidth - 0.5) * 20;
    const y = (clientY / window.innerHeight - 0.5) * 20;
    setMousePos({ x, y });
  };

  // Quick search for pages
  const handleSearch = (e) => {
    e.preventDefault();
    const query = searchQuery.toLowerCase().trim();
    const routeMap = {
      'dashboard': '/dashboard',
      'home': '/',
      'storage': '/dashboard/storage',
      'vm': '/dashboard/vmcluster',
      'virtual machine': '/dashboard/vmcluster',
      'cost': '/dashboard/costs',
      'costs': '/dashboard/costs',
      'billing': '/dashboard/billing',
      'security': '/dashboard/security',
      'settings': '/dashboard/settings',
      'profile': '/dashboard/profile',
      'pricing': '/dashboard/pricing',
      'contact': '/contact',
      'about': '/about',
      'help': '/help',
      'login': '/login',
      'register': '/register',
    };

    const match = Object.keys(routeMap).find(key => query.includes(key));
    if (match) {
      navigate(routeMap[match]);
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className="error-page" onMouseMove={handleMouseMove}>
      <canvas ref={canvasRef} className="error-canvas" />
      
      <div className="error-container" style={{ transform: `translate(${mousePos.x * 0.3}px, ${mousePos.y * 0.3}px)` }}>
        {/* Animated 404 */}
        <div className="error-code-wrapper">
          <div className="error-code" data-text={glitchText}>{glitchText}</div>
          <div className="error-code-shadow">{glitchText}</div>
        </div>

        {/* Title & Description */}
        <h1 className="error-title">Lost in the Cloud</h1>
        <p className="error-description">
          The page <code className="error-path">{location.pathname}</code> doesn't exist in our infrastructure.
          <br />
          It may have been moved, deleted, or never provisioned.
        </p>

        {/* Quick Search */}
        <form className="error-search" onSubmit={handleSearch}>
          <div className="search-input-wrapper">
            <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="Search for a page... (e.g., dashboard, costs, storage)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="error-search-input"
              autoFocus
            />
            <button type="submit" className="search-btn">Go</button>
          </div>
        </form>

        {/* Action Buttons */}
        <div className="error-actions">
          <button onClick={() => navigate(-1)} className="error-btn secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Go Back
          </button>
          <Link to="/" className="error-btn primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Home
          </Link>
          <Link to="/dashboard" className="error-btn accent">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
            Dashboard
          </Link>
        </div>

        {/* Quick Links Grid */}
        <div className="error-quicklinks">
          <p className="quicklinks-title">Quick Navigation</p>
          <div className="quicklinks-grid">
            <Link to="/dashboard/storage" className="quicklink-item">
              <span className="quicklink-icon">📁</span>
              <span>Storage</span>
            </Link>
            <Link to="/dashboard/vmcluster" className="quicklink-item">
              <span className="quicklink-icon">🖥️</span>
              <span>VMs</span>
            </Link>
            <Link to="/dashboard/costs" className="quicklink-item">
              <span className="quicklink-icon">📊</span>
              <span>Costs</span>
            </Link>
            <Link to="/dashboard/security" className="quicklink-item">
              <span className="quicklink-icon">🔒</span>
              <span>Security</span>
            </Link>
            <Link to="/dashboard/settings" className="quicklink-item">
              <span className="quicklink-icon">⚙️</span>
              <span>Settings</span>
            </Link>
            <Link to="/contact" className="quicklink-item">
              <span className="quicklink-icon">💬</span>
              <span>Support</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
