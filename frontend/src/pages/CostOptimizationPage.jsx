import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  IconActivity,
  IconBarChart,
  IconChevronLeft,
  IconClock,
  IconGlobe,
  IconHardDrive,
  IconLightbulb,
  IconPackage,
  IconRefresh,
  IconServer,
  IconTag,
  IconTarget,
  IconZap,
} from '../components/dashboard/Icons.jsx';
import '../styles/costoptimization.css';
import PageRefreshButton from '../components/ui/PageRefreshButton.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';

const providerTips = [
  {
    key: 'aws',
    title: 'AWS Cost Optimization',
    points: [
      ['S3 Intelligent Tiering', 'Automatically moves data between access tiers based on usage patterns. Save up to 70% on storage costs without performance impact.'],
      ['Spot Instances', 'Use for batch processing, CI/CD, and fault-tolerant workloads. Get up to 90% discount compared to On-Demand pricing.'],
      ['Savings Plans', 'Commit to consistent usage per hour and save up to 72% on compute costs.'],
      ['EBS Snapshot Lifecycle', 'Move old snapshots to Amazon S3 Glacier for 80% cost reduction and set automatic lifecycle policies.'],
      ['Lambda vs EC2', 'For intermittent workloads under 15 minutes, Lambda can be far cheaper than running EC2 all month.'],
      ['RDS Reserved Instances', 'Save 40-60% on database costs with one-year or three-year commitments.'],
      ['CloudFront CDN', 'Reduce data transfer costs and improve performance by caching content at edge locations.'],
    ],
  },
  {
    key: 'gcp',
    title: 'GCP Cost Optimization',
    points: [
      ['Sustained Use Discounts', 'Automatic discounts up to 30% for VMs running more than 25% of the month.'],
      ['Preemptible VMs', 'Ideal for batch jobs and fault-tolerant applications, with savings up to 80%.'],
      ['Committed Use Discounts', 'Save up to 57% with three-year Compute Engine commitments.'],
      ['Coldline/Archive Storage', 'Store rarely accessed data at lower rates for backups and archives.'],
      ['Custom Machine Types', 'Match exact vCPU and memory requirements to avoid oversized instances.'],
      ['Cloud CDN', 'Cache content globally and reduce egress costs.'],
      ['BigQuery Flat-Rate Pricing', 'For heavy analytics workloads, flat-rate pricing can reduce costs versus on-demand.'],
    ],
  },
  {
    key: 'azure',
    title: 'Azure Cost Optimization',
    points: [
      ['Azure Hybrid Benefit', 'Use existing Windows Server and SQL Server licenses on Azure to reduce VM costs.'],
      ['Spot VMs', 'Use evictable capacity for batch processing, dev/test environments, and rendering.'],
      ['Reserved Instances', 'Save up to 72% with three-year reservations that can be exchanged.'],
      ['Cool/Archive Blob Storage', 'Use low-cost tiers and automatic tiering for infrequent access.'],
      ['Dev/Test Pricing', 'Apply non-production discounts with Visual Studio subscriptions.'],
      ['Azure Front Door', 'Combine global load balancing and CDN to reduce transfer cost.'],
      ['SQL Database Elastic Pools', 'Share resources across multiple databases for multi-tenant workloads.'],
    ],
  },
];

const strategies = [
  { icon: <IconTarget />, title: 'Right-Sizing Resources', body: 'Monitor actual usage and downsize overprovisioned instances. Most workloads use less than half of allocated resources.', savings: '30-50%' },
  { icon: <IconClock />, title: 'Auto-Scheduling', body: 'Stop dev/test environments outside business hours. Running 9-5 Monday-Friday instead of all month saves heavily.', savings: '60-70%' },
  { icon: <IconHardDrive />, title: 'Storage Tiering', body: 'Use hot storage for frequent access, cool for monthly access, and archive for yearly retrieval.', savings: '50-80%' },
  { icon: <IconActivity />, title: 'Data Compression', body: 'Enable compression for databases and file storage to reduce stored volume without application rewrites.', savings: '50-70%' },
  { icon: <IconGlobe />, title: 'CDN Usage', body: 'Serve static content from edge locations to reduce origin transfer costs and improve latency.', savings: '40-60%' },
  { icon: <IconRefresh />, title: 'Lifecycle Policies', body: 'Automatically transition old data to cheaper storage classes and expire temporary files.', savings: '40-60%' },
  { icon: <IconZap />, title: 'Serverless Architecture', body: 'Use event-driven compute where appropriate so you pay only for actual execution time.', savings: '70-90%' },
  { icon: <IconPackage />, title: 'Containerization', body: 'Use containers for denser workload placement and better resource utilization.', savings: '50-80%' },
  { icon: <IconTag />, title: 'Tag Everything', body: 'Apply consistent cost allocation tags to find unused resources and optimize by team or project.', savings: '20-30%' },
];

const quickWins = [
  ['Delete Unattached Volumes', 'Find and delete EBS volumes, persistent disks, and managed disks not attached to any VM. Average savings: $50-500/month.'],
  ['Stop Idle VMs', 'Identify VMs with less than 5% CPU usage over 7 days. Stop or downsize them. Average savings: $200-2000/month.'],
  ['Clean Up Old Snapshots', "Delete snapshots older than 90 days that are not needed. Move others to cheaper storage. Average savings: $100-1000/month."],
  ['Remove Unused Load Balancers', 'Identify load balancers with zero traffic. Each idle load balancer costs around $15-20/month.'],
  ['Optimize Data Transfer', 'Use private network transfers and keep traffic within the same region or zone where possible.'],
];

const monitoringCards = [
  ['Budget Alerts', ['Set monthly budget thresholds at 50%, 80%, and 100%', 'Configure email/SMS notifications', 'Create separate budgets per project/environment']],
  ['Anomaly Detection', ['Enable cloud provider anomaly detection services', 'Set up alerts for large day-over-day cost increases', 'Review anomalies weekly']],
  ['Regular Reviews', ['Weekly: review top 10 most expensive resources', 'Monthly: analyze trends and optimize', 'Quarterly: review reserved instance utilization']],
];

const CostOptimizationPage = () => {
  const navigate = useNavigate();
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  return (
    <div className="cost-optimization-container">
      <div className="optimization-header">
        <button className="back-button" type="button" onClick={() => navigate('/dashboard/costs')}>
          <IconChevronLeft aria-hidden="true" />
          Back to Cost Analysis
        </button>
        <div className="optimization-header-row">
          <div>
            <span className="page-kicker">Optimization Playbook</span>
            <h1>
              <span className="heading-icon"><IconLightbulb aria-hidden="true" /></span>
              Cost Optimization Guide
            </h1>
            <p>Strategies to reduce cloud spending across AWS, GCP, and Azure.</p>
          </div>
          <PageRefreshButton
            onClick={() =>
              runPageRefresh(async () => {}, {
                loadingMessage: 'Refreshing optimization guide…',
                successMessage: 'Optimization guide refreshed.',
              })
            }
            busy={pageRefreshing}
          />
        </div>
      </div>

      <section className="tips-section" aria-labelledby="provider-savings-heading">
        <h2 id="provider-savings-heading">Provider-Specific Savings</h2>
        <div className="tips-grid">
          {providerTips.map((provider) => (
            <article key={provider.key} className={`tip-card ${provider.key}-card`}>
              <h3>
                <span className={`provider-mark ${provider.key}`}>{provider.key.toUpperCase()}</span>
                {provider.title}
              </h3>
              <ul>
                {provider.points.map(([title, body]) => (
                  <li key={title}>
                    <strong>{title}:</strong> {body}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="general-strategies" aria-labelledby="strategies-heading">
        <h2 id="strategies-heading">Universal Multi-Cloud Strategies</h2>
        <div className="strategy-grid">
          {strategies.map((strategy) => (
            <article key={strategy.title} className="strategy-card">
              <div className="strategy-icon" aria-hidden="true">{strategy.icon}</div>
              <h3>{strategy.title}</h3>
              <p>{strategy.body}</p>
              <div className="strategy-impact">
                <span className="impact-label">Potential Savings</span>
                <span className="impact-value">{strategy.savings}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="quick-wins" aria-labelledby="quick-wins-heading">
        <h2 id="quick-wins-heading">
          <IconZap aria-hidden="true" />
          Quick Wins
        </h2>
        <div className="wins-list">
          {quickWins.map(([title, body], index) => (
            <article className="win-item" key={title}>
              <span className="win-number">{index + 1}</span>
              <div className="win-content">
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="monitoring-section" aria-labelledby="monitoring-heading">
        <h2 id="monitoring-heading">
          <IconBarChart aria-hidden="true" />
          Cost Monitoring
        </h2>
        <div className="monitoring-grid">
          {monitoringCards.map(([title, items]) => (
            <article className="monitoring-card" key={title}>
              <h3>{title}</h3>
              <ul>
                {items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};

export default CostOptimizationPage;
