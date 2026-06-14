import React from 'react';

/**
 * Standard content section for dashboard pages.
 */
export default function Panel({
  title,
  description,
  actions,
  children,
  className = '',
  as: Component = 'section',
  id,
  ...rest
}) {
  return (
    <Component
      id={id}
      className={['enterprise-panel', className].filter(Boolean).join(' ')}
      {...rest}
    >
      {(title || description || actions) && (
        <header className="enterprise-panel__header">
          <div className="enterprise-panel__header-text">
            {title ? <h2 className="enterprise-panel__title">{title}</h2> : null}
            {description ? <p className="enterprise-panel__desc">{description}</p> : null}
          </div>
          {actions ? <div className="enterprise-panel__actions">{actions}</div> : null}
        </header>
      )}
      {children}
    </Component>
  );
}
