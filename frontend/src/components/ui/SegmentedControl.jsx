import React from 'react';

/**
 * Accessible segmented control for tabs and filters.
 * Options may include: badge, locked, onLockedClick
 */
export default function SegmentedControl({
  options,
  value,
  onChange,
  className = '',
  ariaLabel = 'Options',
}) {
  return (
    <div className={['enterprise-segmented', className].filter(Boolean).join(' ')} role="group" aria-label={ariaLabel}>
      {options.map((option) => {
        const active = value === option.value;
        const locked = Boolean(option.locked);
        return (
          <button
            key={option.value}
            type="button"
            className={[
              'enterprise-segmented__btn',
              active ? 'is-active' : '',
              locked ? 'enterprise-segmented__btn--locked' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-pressed={active}
            aria-disabled={locked || undefined}
            onClick={() => {
              if (locked) {
                option.onLockedClick?.();
                return;
              }
              onChange(option.value);
            }}
          >
            {option.icon ? <span className="enterprise-segmented__icon" aria-hidden>{option.icon}</span> : null}
            <span>{option.label}</span>
            {option.badge != null && option.badge !== '' ? (
              <span className="enterprise-segmented__badge">{option.badge}</span>
            ) : null}
            {locked ? <span className="enterprise-segmented__lock" aria-hidden>Locked</span> : null}
          </button>
        );
      })}
    </div>
  );
}
