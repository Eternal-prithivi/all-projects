import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import '../styles/breadcrumbs.css';

const Breadcrumbs = () => {
  const location = useLocation();
  
  const pathnames = location.pathname.split('/').filter(x => x);
  
  const formatPathname = (name) => {
    return name
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (pathnames.length === 0) return null;

  return (
    <nav className="breadcrumbs">
      <Link to="/dashboard" className="breadcrumb-item">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 1l7 6v8H1V7l7-6zm0 1.5L2 8v6h12V8L8 2.5z"/>
        </svg>
        Home
      </Link>
      {pathnames.map((name, index) => {
        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
        const isLast = index === pathnames.length - 1;
        
        return (
          <React.Fragment key={routeTo}>
            <span className="breadcrumb-separator">/</span>
            {isLast ? (
              <span className="breadcrumb-item active">{formatPathname(name)}</span>
            ) : (
              <Link to={routeTo} className="breadcrumb-item">
                {formatPathname(name)}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumbs;
