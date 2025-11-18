import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/global-search.css';

const GlobalSearch = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const searchItems = [
    { id: 1, title: 'Dashboard Overview', path: '/dashboard', icon: '📊', keywords: ['home', 'stats', 'overview'] },
    { id: 2, title: 'VM Cluster Management', path: '/dashboard/vmcluster', icon: '🖥️', keywords: ['vm', 'virtual machine', 'server', 'compute'] },
    { id: 3, title: 'Storage Management', path: '/dashboard/storage', icon: '💾', keywords: ['storage', 'files', 'upload', 's3', 'gcp', 'azure'] },
    { id: 4, title: 'Cost Analysis', path: '/dashboard/costs', icon: '💰', keywords: ['costs', 'budget', 'billing', 'expenses'] },
    { id: 5, title: 'Security Center', path: '/dashboard/security', icon: '🔒', keywords: ['security', '2fa', 'encryption', 'audit'] },
    { id: 6, title: 'Cost Simulator', path: '/dashboard/cost-simulator', icon: '🎯', keywords: ['simulator', 'forecast', 'prediction'] },
    { id: 7, title: 'Cost Optimization', path: '/dashboard/cost-optimization', icon: '⚡', keywords: ['optimize', 'savings', 'recommendations'] },
  ];

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

    const filtered = searchItems.filter(item => {
      const searchTerm = query.toLowerCase();
      return (
        item.title.toLowerCase().includes(searchTerm) ||
        item.keywords.some(keyword => keyword.includes(searchTerm))
      );
    });

    setResults(filtered);
  }, [query]);

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
      <div className="global-search-modal" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
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
            {searchItems.slice(0, 5).map((item) => (
              <button
                key={item.id}
                className="search-result-item"
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
