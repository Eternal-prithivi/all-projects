import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';

const ThemeContext = createContext(null);

const STORAGE_KEY = 'zenith-theme';

/**
 * Resolve a theme preference to an effective theme (dark or light).
 * "auto" resolves based on OS prefers-color-scheme.
 */
const resolveEffective = (preference) => {
  if (preference === 'auto') {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  return preference === 'light' ? 'light' : 'dark';
};

/**
 * Apply theme to the DOM immediately.
 * Sets data-theme attribute on <html> and updates color-scheme.
 */
const applyThemeToDOM = (effectiveTheme) => {
  document.documentElement.dataset.theme = effectiveTheme;
  document.documentElement.style.colorScheme = effectiveTheme;
};

export const ThemeProvider = ({ children }) => {
  // Read saved preference from localStorage (default: dark)
  const [theme, setThemeState] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dark';
    } catch {
      return 'dark';
    }
  });

  const [effectiveTheme, setEffectiveTheme] = useState(() => resolveEffective(theme));

  // Apply theme on mount and whenever preference changes
  useEffect(() => {
    const resolved = resolveEffective(theme);
    setEffectiveTheme(resolved);
    applyThemeToDOM(resolved);

    // Save to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage not available
    }
  }, [theme]);

  // Listen for OS theme changes when in "auto" mode
  useEffect(() => {
    if (theme !== 'auto') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');

    const handleChange = (e) => {
      const resolved = e.matches ? 'light' : 'dark';
      setEffectiveTheme(resolved);
      applyThemeToDOM(resolved);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  const setTheme = useCallback((newTheme) => {
    const valid = ['dark', 'light', 'auto'];
    if (valid.includes(newTheme)) {
      setThemeState(newTheme);
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
