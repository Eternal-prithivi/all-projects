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

function isAllowedDuringMaintenance(pathname) {
  if (pathname === '/') return true;
  return ALLOWED_PREFIXES.some((p) => pathname === p || pathname.startsWith(p));
}

export default function MaintenanceGate({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(apiUrl('/platform/status'));
        if (!res.ok) {
          if (!cancelled) setChecked(true);
          return;
        }
        const data = await res.json();
        if (
          !cancelled &&
          data.maintenance_mode &&
          !isAllowedDuringMaintenance(location.pathname)
        ) {
          navigate('/503', { replace: true });
        }
      } catch {
        /* API unreachable — allow app to load */
      }
      if (!cancelled) setChecked(true);
    };

    check();
    return () => {
      cancelled = true;
    };
  }, [location.pathname, navigate]);

  if (!checked) return children;

  return children;
}
