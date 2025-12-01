import React from 'react';
import '../styles/skeletons.css';

/**
 * Card Skeleton - For dashboard cards, stat cards, etc.
 */
export const CardSkeleton = () => (
  <div className="skeleton-card">
    <div className="skeleton skeleton-title"></div>
    <div className="skeleton skeleton-text"></div>
    <div className="skeleton skeleton-text skeleton-text-short"></div>
  </div>
);

/**
 * VM Card Skeleton - For VM cluster page
 */
export const VMCardSkeleton = () => (
  <div className="skeleton-vm-card">
    <div className="skeleton-vm-header">
      <div className="skeleton skeleton-circle"></div>
      <div className="skeleton skeleton-vm-name"></div>
    </div>
    <div className="skeleton-vm-body">
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text skeleton-text-short"></div>
    </div>
    <div className="skeleton-vm-footer">
      <div className="skeleton skeleton-button"></div>
    </div>
  </div>
);

/**
 * Table Skeleton - For data tables
 */
export const TableSkeleton = ({ rows = 5, columns = 4 }) => (
  <div className="skeleton-table">
    <div className="skeleton-table-header">
      {[...Array(columns)].map((_, i) => (
        <div key={i} className="skeleton skeleton-table-header-cell"></div>
      ))}
    </div>
    <div className="skeleton-table-body">
      {[...Array(rows)].map((_, rowIndex) => (
        <div key={rowIndex} className="skeleton-table-row">
          {[...Array(columns)].map((_, colIndex) => (
            <div key={colIndex} className="skeleton skeleton-table-cell"></div>
          ))}
        </div>
      ))}
    </div>
  </div>
);

/**
 * Chart Skeleton - For cost analysis charts
 */
export const ChartSkeleton = () => (
  <div className="skeleton-chart">
    <div className="skeleton skeleton-chart-title"></div>
    <div className="skeleton-chart-area">
      <div className="skeleton-chart-bars">
        {[60, 80, 45, 90, 70, 55, 85].map((height, i) => (
          <div 
            key={i} 
            className="skeleton skeleton-chart-bar" 
            style={{ height: `${height}%` }}
          ></div>
        ))}
      </div>
    </div>
  </div>
);

/**
 * Storage Card Skeleton - For storage page
 */
export const StorageCardSkeleton = () => (
  <div className="skeleton-storage-card">
    <div className="skeleton-storage-icon">
      <div className="skeleton skeleton-circle-lg"></div>
    </div>
    <div className="skeleton skeleton-storage-title"></div>
    <div className="skeleton skeleton-text"></div>
    <div className="skeleton skeleton-text skeleton-text-short"></div>
    <div className="skeleton skeleton-progress-bar"></div>
  </div>
);

/**
 * Dashboard Grid Skeleton - Full dashboard loading state
 */
export const DashboardSkeleton = () => (
  <div className="skeleton-dashboard">
    {/* Stats Row */}
    <div className="skeleton-stats-grid">
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
    </div>

    {/* Charts Row */}
    <div className="skeleton-charts-grid">
      <ChartSkeleton />
      <ChartSkeleton />
    </div>

    {/* Table */}
    <TableSkeleton rows={6} columns={5} />
  </div>
);

/**
 * VM Cluster Grid Skeleton
 */
export const VMClusterSkeleton = () => (
  <div className="skeleton-vm-grid">
    <VMCardSkeleton />
    <VMCardSkeleton />
    <VMCardSkeleton />
    <VMCardSkeleton />
  </div>
);

/**
 * Generic Page Skeleton
 */
export const PageSkeleton = () => (
  <div className="skeleton-page">
    <div className="skeleton skeleton-page-title"></div>
    <div className="skeleton skeleton-text"></div>
    <div className="skeleton skeleton-text"></div>
    <div className="skeleton skeleton-text skeleton-text-short"></div>
    
    <div className="skeleton-content-grid">
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
    </div>
  </div>
);

/**
 * List Skeleton - For lists of items
 */
export const ListSkeleton = ({ items = 5 }) => (
  <div className="skeleton-list">
    {[...Array(items)].map((_, i) => (
      <div key={i} className="skeleton-list-item">
        <div className="skeleton skeleton-circle"></div>
        <div className="skeleton-list-content">
          <div className="skeleton skeleton-text"></div>
          <div className="skeleton skeleton-text skeleton-text-short"></div>
        </div>
      </div>
    ))}
  </div>
);

/**
 * Profile Skeleton - For profile page
 */
export const ProfileSkeleton = () => (
  <div className="skeleton-profile">
    <div className="skeleton-profile-header">
      <div className="skeleton skeleton-avatar"></div>
      <div className="skeleton-profile-info">
        <div className="skeleton skeleton-profile-name"></div>
        <div className="skeleton skeleton-text skeleton-text-short"></div>
      </div>
    </div>
    <div className="skeleton-profile-content">
      <CardSkeleton />
      <CardSkeleton />
    </div>
  </div>
);

export default {
  CardSkeleton,
  VMCardSkeleton,
  TableSkeleton,
  ChartSkeleton,
  StorageCardSkeleton,
  DashboardSkeleton,
  VMClusterSkeleton,
  PageSkeleton,
  ListSkeleton,
  ProfileSkeleton,
};
