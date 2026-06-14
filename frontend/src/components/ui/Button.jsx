import React from 'react';

const VARIANT_CLASS = {
  primary: 'zenith-btn--primary',
  secondary: 'zenith-btn--secondary',
  danger: 'zenith-btn--danger',
  ghost: 'zenith-btn--ghost',
};

const SIZE_CLASS = {
  sm: 'zenith-btn--sm',
  md: '',
  lg: 'zenith-btn--lg',
};

/**
 * Shared button primitive for dashboard actions.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  type = 'button',
  className = '',
  children,
  as: Component = 'button',
  ...props
}) {
  const classes = [
    'zenith-btn',
    VARIANT_CLASS[variant] || VARIANT_CLASS.primary,
    SIZE_CLASS[size] || '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Component type={Component === 'button' ? type : undefined} className={classes} {...props}>
      {children}
    </Component>
  );
}
