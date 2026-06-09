// =============================================================================
// COMPONENT: GlobalSearch.jsx  (145 lines)
// PURPOSE: ⌘K command-palette-style search modal — searches pages, commands, files
//   - Triggered by: Header search button or keyboard shortcut ⌘K / Ctrl+K (not while typing in fields)
//   - Searches: page names (routes), quick actions, recent files
//   - Results are navigated with arrow keys, Enter confirms, Escape closes
//   - data-tour="global-search" on the trigger button in Header.jsx
// USED BY: Header.jsx (as modal, triggered from search button)
// DO NOT:
//   - Add live backend search here — results come from static route map + sessionStorage
//   - Remove keyboard event listeners without replacing them — ⌘K is a user expectation
//   - Change the result shape without updating Header.jsx trigger props
// =============================================================================
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import {
  IconActivity,
  IconBarChart,
  IconDashboard,
  IconDollarSign,
  IconHardDrive,
  IconLock,
  IconSearch,
  IconServer,
  IconShieldCheck,
  IconTarget,
  IconZap,
} from './dashboard/Icons.jsx';
import '../styles/global-search.css';

const SEARCH_ITEMS = [
  { id: 1, title: 'Dashboard Overview', path: '/dashboard', icon: <IconDashboard />, keywords: ['home', 'stats', 'overview'] },
  { id: 2, title: 'VM Cluster Management', path: '/dashboard/vmcluster', icon: <IconServer />, keywords: ['vm', 'virtual machine', 'server', 'compute'] },
  { id: 3, title: 'Storage Management', path: '/dashboard/storage', icon: <IconHardDrive />, keywords: ['storage', 'files', 'upload', 's3', 'gcp', 'azure'] },
  { id: 4, title: 'Cost Analysis', path: '/dashboard/costs', icon: <IconDollarSign />, keywords: ['costs', 'budget', 'billing', 'expenses'] },
  { id: 5, title: 'Security Center', path: '/dashboard/security', icon: <IconShieldCheck />, keywords: ['security', '2fa', 'encryption', 'audit'] },
  { id: 6, title: 'Cost Simulator', path: '/dashboard/simulator', icon: <IconTarget />, keywords: ['simulator', 'forecast', 'prediction'] },
  { id: 7, title: 'Cost Optimization', path: '/dashboard/optimization', icon: <IconZap />, keywords: ['optimize', 'savings', 'recommendations'] },
  { id: 8, title: 'Security Settings', path: '/dashboard/security-settings', icon: <IconLock />, keywords: ['password', '2fa', 'sessions', 'audit'] },
  { id: 9, title: 'Activity', path: '/dashboard/profile', icon: <IconActivity />, keywords: ['profile', 'activity', 'account'] },
  { id: 10, title: 'Notifications', path: '/dashboard/notifications', icon: <IconActivity />, keywords: ['notifications', 'alerts'] },
];

const ADMIN_SEARCH_ITEMS = [
  { id: 101, title: 'Admin Overview', path: '/admin', icon: <IconDashboard />, keywords: ['admin', 'overview'] },
  { id: 102, title: 'User Management', path: '/admin/users', icon: <IconServer />, keywords: ['users', 'ban', 'roles'] },
  { id: 103, title: 'Admin Analytics', path: '/admin/analytics', icon: <IconBarChart />, keywords: ['analytics', 'reports'] },
  { id: 104, title: 'Payments', path: '/admin/payments', icon: <IconDollarSign />, keywords: ['payments', 'razorpay'] },
  { id: 105, title: 'System Health', path: '/admin/system', icon: <IconShieldCheck />, keywords: ['system', 'health', 'audit'] },
  { id: 106, title: 'Admin Settings', path: '/admin/settings', icon: <IconLock />, keywords: ['admin settings', 'platform'] },
  { id: 107, title: 'Admin Notifications', path: '/admin/notifications', icon: <IconActivity />, keywords: ['notifications', 'alerts'] },
];

const GlobalSearch = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { user } = useAuth();

  const searchItems = useMemo(
    () => (user?.role === 'admin' ? [...SEARCH_ITEMS, ...ADMIN_SEARCH_ITEMS] : SEARCH_ITEMS),
    [user?.role]
  );

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (query.trim() === '') {
      setResults([]);
      return;
    }

    const filtered = searchItems.filter((item) => {
      const searchTerm = query.toLowerCase();
      return (
        item.title.toLowerCase().includes(searchTerm) ||
        item.keywords.some(keyword => keyword.includes(searchTerm))
      );
    });

    setResults(filtered);
  }, [query, searchItems]);

  const handleSelect = (path) => {
    navigate(path);
    setQuery('');
    setResults([]);
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="global-search-overlay" onClick={onClose}>
      <div
        className="global-search-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="global-search-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="global-search-title" className="sr-only">Global search</h2>
        <div className="search-input-wrapper">
          <span className="search-icon"><IconSearch /></span>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
            aria-label="Search pages"
            placeholder="Search pages... (Press ESC to close)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="search-hint">ESC</kbd>
        </div>

        {query && results.length > 0 && (
          <div className="search-results">
            {results.map((result) => (
              <button
                key={result.id}
                className="search-result-item"
                type="button"
                aria-label={`Open ${result.title}`}
                onClick={() => handleSelect(result.path)}
              >
                <span className="result-icon">{result.icon}</span>
                <span className="result-title">{result.title}</span>
                <span className="result-path">{result.path}</span>
              </button>
            ))}
          </div>
        )}

        {query && results.length === 0 && (
          <div className="search-no-results">
            <p>No results found for "{query}"</p>
          </div>
        )}

        {!query && (
          <div className="search-suggestions">
            <p className="suggestions-title">Popular Pages</p>
            {searchItems.slice(0, 6).map((item) => (
              <button
                key={item.id}
                className="search-result-item"
                type="button"
                aria-label={`Open ${item.title}`}
                onClick={() => handleSelect(item.path)}
              >
                <span className="result-icon">{item.icon}</span>
                <span className="result-title">{item.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalSearch;
