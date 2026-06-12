import React, { useState } from 'react';
import { getSetupGuide } from '../../data/byocSetupGuides';

export default function ByocSetupGuidePanel({ tier, defaultOpen = false, className = '' }) {
  const guide = getSetupGuide(tier);
  const [open, setOpen] = useState(defaultOpen);
  if (!guide) return null;

  return (
    <div className={`byoc-setup-guide ${className}`.trim()}>
      <button
        type="button"
        className="byoc-setup-guide__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? 'Hide setup guide' : 'How to get these credentials'}
      </button>
      {open && (
        <div className="byoc-setup-guide__body">
          <p className="byoc-setup-guide__lead">
            <strong>Recommended, not required.</strong> You can connect storage now and return here anytime.
          </p>
          <div className="byoc-setup-guide__matrix">
            <div>
              <strong>Works if you skip:</strong>
              <p>{guide.worksWithout.join(' · ')}</p>
            </div>
            <div>
              <strong>Blocked until complete:</strong>
              <p>{guide.blockedWithout.join(' · ')}</p>
            </div>
          </div>
          <ol className="byoc-setup-guide__steps">
            {guide.steps.map((step, i) => (
              <li key={step.title}>
                <strong>{i + 1}. {step.title}</strong>
                <p>{step.body}</p>
                {step.link && (
                  <a href={step.link} target="_blank" rel="noopener noreferrer">
                    {step.linkLabel || 'Open console'}
                  </a>
                )}
              </li>
            ))}
          </ol>
          <div className="byoc-setup-guide__checklist">
            <strong>Fields to copy</strong>
            <ul>
              {guide.fieldChecklist.map((f) => (
                <li key={f.key}>
                  <code>{f.label}</code>
                  {f.example ? ` — e.g. ${f.example}` : ''}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
