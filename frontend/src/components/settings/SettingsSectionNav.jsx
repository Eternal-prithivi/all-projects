import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { SETTINGS_SECTIONS } from '../../config/settingsNavConfig.js';

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

export default function SettingsSectionNav() {
  const location = useLocation();
  const [activeId, setActiveId] = useState(SETTINGS_SECTIONS[0]?.id || '');

  useEffect(() => {
    const hash = location.hash.replace('#', '');
    if (hash) {
      requestAnimationFrame(() => scrollToSection(hash));
      setActiveId(hash);
    }
  }, [location.hash]);

  useEffect(() => {
    const sectionEls = SETTINGS_SECTIONS
      .map((s) => document.getElementById(s.id))
      .filter(Boolean);

    if (sectionEls.length === 0) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target?.id) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] },
    );

    sectionEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const handleClick = (e, id) => {
    e.preventDefault();
    setActiveId(id);
    scrollToSection(id);
    window.history.replaceState(null, '', `${location.pathname}#${id}`);
  };

  return (
    <nav className="zenith-settings-hub" aria-label="Settings sections">
      {SETTINGS_SECTIONS.map((section) => (
        <a
          key={section.id}
          href={`#${section.id}`}
          className={activeId === section.id ? 'active' : undefined}
          aria-current={activeId === section.id ? 'location' : undefined}
          onClick={(e) => handleClick(e, section.id)}
        >
          {section.label}
        </a>
      ))}
    </nav>
  );
}
