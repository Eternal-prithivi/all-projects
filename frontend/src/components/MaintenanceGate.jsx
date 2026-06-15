import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiUrl } from '../config/apiBase.js';

const ALLOWED_PREFIXES = [
  '/503',
  '/500',
  '/status',
  '/contact',
  '/legal/',
  '/trust',
  '/help',
  '/support',
  '/about',
  '/features',
];

const PLATFORM_STATUS_KEY = 'zenith_platform_status';
const PLATFORM_STATUS_TTL_MS = 60 * 1000;

function isAllowedDuringMaintenance(pathname) {
  if (pathname === '/') return true;
  return ALLOWED_PREFIXES.some((p) => pathname === p || pathname.startsWith(p));
}

function readPlatformStatusCache() {
  try {
    const raw = sessionStorage.getItem(PLATFORM_STATUS_KEY);
    if (!raw) return null;
    const { data, ts } = JSON.parse(raw);
    if (!data || Date.now() - ts > PLATFORM_STATUS_TTL_MS) {
      sessionStorage.removeItem(PLATFORM_STATUS_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

function writePlatformStatusCache(data) {
  try {
    sessionStorage.setItem(PLATFORM_STATUS_KEY, JSON.stringify({ data, ts: Date.now() }));
  } catch {
    /* ignore */
  }
}

export default function MaintenanceGate({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const applyMaintenanceRedirect = (data) => {
      if (
        !cancelled &&
        data?.maintenance_mode &&
        !isAllowedDuringMaintenance(location.pathname)
      ) {
        navigate('/503', { replace: true });
      }
    };

    const cached = readPlatformStatusCache();
    if (cached) {
      applyMaintenanceRedirect(cached);
      if (!cancelled) setChecked(true);
      return () => {
        cancelled = true;
      };
    }

    const check = async () => {
      try {
        const res = await fetch(apiUrl('/platform/status'));
        if (!res.ok) {
          if (!cancelled) setChecked(true);
          return;
        }
        const data = await res.json();
        writePlatformStatusCache(data);
        applyMaintenanceRedirect(data);
      } catch {
        /* API unreachable — allow app to load */
      }
      if (!cancelled) setChecked(true);
    };

    check();
    return () => {
      cancelled = true;
    };
    // Check once per mount / TTL expiry — not on every navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  if (!checked) return children;

  return children;
}
