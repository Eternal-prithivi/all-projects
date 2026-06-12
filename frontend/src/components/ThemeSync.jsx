// Syncs theme preference from PreferencesContext (no extra /settings fetch).
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { usePreferences } from "../context/PreferencesContext";

const VALID_THEMES = new Set(["dark", "light", "auto"]);

export default function ThemeSync() {
  const { isAuthenticated } = useAuth();
  const { setTheme } = useTheme();
  const { preferences, isLoaded } = usePreferences();

  useEffect(() => {
    if (!isAuthenticated || !isLoaded) return;
    const serverTheme = preferences?.theme;
    if (serverTheme && VALID_THEMES.has(serverTheme)) {
      setTheme(serverTheme);
    }
  }, [isAuthenticated, isLoaded, preferences?.theme, setTheme]);

  return null;
}
