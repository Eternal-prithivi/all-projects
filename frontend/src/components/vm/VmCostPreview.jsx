import React from "react";

function formatUsd(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 100 ? 0 : 2,
  }).format(Number(value));
}

function formatUsdRange(min, max) {
  if (min == null || max == null) return "—";
  if (Math.abs(min - max) < 0.01) return formatUsd(min);
  return `${formatUsd(min)} – ${formatUsd(max)}`;
}

export default function VmCostPreview({
  estimate,
  range,
  loading = false,
  compact = false,
  className = "",
}) {
  if (loading) {
    return (
      <div className={`vm-cost-preview vm-cost-preview--loading ${className}`.trim()}>
        <span className="vm-cost-preview__spinner" aria-hidden />
        <span>Estimating cost…</span>
      </div>
    );
  }

  if (!estimate && !range) return null;

  if (range && !estimate) {
    return (
      <aside className={`vm-cost-preview ${className}`.trim()} aria-label="Estimated cost overview">
        <div className="vm-cost-preview__header">
          <h4 className="vm-cost-preview__title">Estimated cost overview</h4>
          <span className="vm-cost-preview__badge">Approximate</span>
        </div>
        <p className="vm-cost-preview__headline">
          <strong>{formatUsdRange(range.min_monthly_usd, range.max_monthly_usd)}</strong>
          <span className="vm-cost-preview__unit"> / month if always on</span>
        </p>
        <p className="vm-cost-preview__sub">
          {formatUsdRange(range.min_hourly_usd, range.max_hourly_usd)} per hour · tier depends on slot assigned
        </p>
        {range.ephemeral_note && (
          <p className="vm-cost-preview__note">{range.ephemeral_note}</p>
        )}
        {range.disclaimer && (
          <p className="vm-cost-preview__disclaimer">{range.disclaimer}</p>
        )}
      </aside>
    );
  }

  const usage = estimate.usage_examples || [];
  const alwaysOn = usage.find((u) => u.id === "always_on") || usage[0];
  const business = usage.find((u) => u.id === "business_hours");
  const light = usage.find((u) => u.id === "light");

  return (
    <aside className={`vm-cost-preview ${compact ? "vm-cost-preview--compact" : ""} ${className}`.trim()} aria-label="Estimated cost overview">
      <div className="vm-cost-preview__header">
        <h4 className="vm-cost-preview__title">Estimated cost overview</h4>
        <span className="vm-cost-preview__badge">Approximate</span>
      </div>

      <p className="vm-cost-preview__headline">
        <strong>{formatUsd(estimate.total_monthly_usd)}</strong>
        <span className="vm-cost-preview__unit"> / month if always on</span>
      </p>
      <p className="vm-cost-preview__sub">
        ~{formatUsd(estimate.hourly_usd)} per hour · {estimate.machine_type} on {estimate.csp}
        {estimate.tier_label ? ` (${estimate.tier_label})` : ""}
      </p>

      {!compact && estimate.line_items?.length > 0 && (
        <ul className="vm-cost-preview__breakdown">
          {estimate.line_items.map((item) => (
            <li key={item.name}>
              <span>{item.name}</span>
              <span>{formatUsd(item.monthly_usd)}/mo</span>
            </li>
          ))}
        </ul>
      )}

      {!compact && (business || light) && (
        <div className="vm-cost-preview__usage">
          <span className="vm-cost-preview__usage-label">Usage examples</span>
          <ul>
            {business && (
              <li>
                <span>{business.label}</span>
                <span>~{formatUsd(business.estimated_usd)}</span>
              </li>
            )}
            {light && (
              <li>
                <span>{light.label}</span>
                <span>~{formatUsd(light.estimated_usd)}</span>
              </li>
            )}
          </ul>
        </div>
      )}

      {alwaysOn && compact && (
        <p className="vm-cost-preview__sub">
          Light use (~40h/mo): ~{formatUsd(light?.estimated_usd ?? alwaysOn.estimated_usd * 0.055)}
        </p>
      )}

      {estimate.ephemeral_note && (
        <p className="vm-cost-preview__note">{estimate.ephemeral_note}</p>
      )}
      {estimate.disclaimer && (
        <p className="vm-cost-preview__disclaimer">{estimate.disclaimer}</p>
      )}
    </aside>
  );
}
