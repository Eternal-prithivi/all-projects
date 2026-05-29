import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import '../styles/cookie-consent.css';

const STORAGE_KEY = 'zenith_cookie_consent';

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) setVisible(true);
    } catch {
      setVisible(true);
    }
  }, []);

  const save = (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="cookie-consent" role="dialog" aria-label="Cookie consent">
      <div className="cookie-consent__inner">
        <p className="cookie-consent__text">
          We use essential cookies to keep you signed in and remember preferences. Optional analytics
          help us improve Zenith. See our <Link to="/legal/cookies">Cookie Policy</Link>.
        </p>
        <div className="cookie-consent__actions">
          <button type="button" className="cookie-consent__btn cookie-consent__btn--secondary" onClick={() => save('essential')}>
            Essential only
          </button>
          <button type="button" className="cookie-consent__btn cookie-consent__btn--primary" onClick={() => save('all')}>
            Accept all
          </button>
        </div>
      </div>
    </div>
  );
}
