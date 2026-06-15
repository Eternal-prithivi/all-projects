import React, { Suspense, lazy } from 'react';

const SparklineChartInner = lazy(() => import('./SparklineChartInner.jsx'));

/**
 * Lazy-loaded sparkline — defers recharts until the chart is rendered.
 */
function SparklineChart(props) {
  if (!props.data?.length) return null;

  return (
    <Suspense
      fallback={
        <div
          className="sparkline-chart-wrapper sparkline-chart-wrapper--loading"
          style={{ height: props.height || 120 }}
          aria-hidden="true"
        />
      }
    >
      <SparklineChartInner {...props} />
    </Suspense>
  );
}

export default SparklineChart;
