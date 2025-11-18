import React, { useEffect } from 'react';
import '../styles/keyboard-shortcuts.css';

const KeyboardShortcuts = ({ isOpen, onClose }) => {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const shortcuts = [
    { key: '?', description: 'Show/hide keyboard shortcuts' },
    { key: '/', description: 'Focus search bar' },
    { key: 'N', description: 'Request new VM' },
    { key: 'U', description: 'Upload file' },
    { key: 'C', description: 'View cost analysis' },
    { key: 'ESC', description: 'Close modals' },
    { key: '⌘/Ctrl + K', description: 'Quick command palette' },
  ];

  return (
    <div className="keyboard-shortcuts-overlay" onClick={onClose}>
      <div className="keyboard-shortcuts-modal" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-header">
          <h2>⌨️ Keyboard Shortcuts</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="shortcuts-list">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="shortcut-item">
              <kbd className="shortcut-key">{shortcut.key}</kbd>
              <span className="shortcut-description">{shortcut.description}</span>
            </div>
          ))}
        </div>
        <div className="shortcuts-footer">
          <p>Press <kbd>ESC</kbd> to close this dialog</p>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcuts;
