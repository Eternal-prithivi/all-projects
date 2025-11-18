import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/costoptimization.css';

const CostOptimizationPage = () => {
  const navigate = useNavigate();

  return (
    <div className="cost-optimization-container">
      <div className="optimization-header">
        <button className="back-button" onClick={() => navigate('/dashboard/costs')}>
          ← Back to Cost Analysis
        </button>
        <h1>💡 Cost Optimization Guide</h1>
        <p>Strategies to reduce your cloud spending across AWS, GCP, and Azure</p>
      </div>

      {/* Provider-Specific Tips */}
      <div className="tips-section">
        <h2>Provider-Specific Savings</h2>
        <div className="tips-grid">
          <div className="tip-card aws-card">
            <h3>🔵 AWS Cost Optimization</h3>
            <ul>
              <li>
                <strong>S3 Intelligent Tiering:</strong> Automatically moves data between access tiers based on usage patterns. Save up to 70% on storage costs without performance impact.
              </li>
              <li>
                <strong>Spot Instances:</strong> Use for batch processing, CI/CD, and fault-tolerant workloads. Get up to 90% discount compared to On-Demand pricing.
              </li>
              <li>
                <strong>Savings Plans:</strong> More flexible than Reserved Instances. Commit to consistent usage ($/hour) and save up to 72% on compute costs.
              </li>
              <li>
                <strong>EBS Snapshot Lifecycle:</strong> Move old snapshots to Amazon S3 Glacier for 80% cost reduction. Set automatic lifecycle policies.
              </li>
              <li>
                <strong>Lambda vs EC2:</strong> For intermittent workloads running less than 15 minutes, Lambda can be 10x cheaper than running EC2 24/7.
              </li>
              <li>
                <strong>RDS Reserved Instances:</strong> Save 40-60% on database costs with 1-year or 3-year commitments.
              </li>
              <li>
                <strong>CloudFront CDN:</strong> Reduce data transfer costs by 60% and improve performance by caching content at edge locations.
              </li>
            </ul>
          </div>

          <div className="tip-card gcp-card">
            <h3>🟢 GCP Cost Optimization</h3>
            <ul>
              <li>
                <strong>Sustained Use Discounts:</strong> Automatic discounts up to 30% for VMs running more than 25% of the month. No upfront commitment needed.
              </li>
              <li>
                <strong>Preemptible VMs:</strong> Perfect for batch jobs and fault-tolerant applications. Save up to 80% compared to regular VMs.
              </li>
              <li>
                <strong>Committed Use Discounts:</strong> Save 57% with 3-year commitments on Compute Engine. More flexible than AWS Reserved Instances.
              </li>
              <li>
                <strong>Coldline/Archive Storage:</strong> Store rarely accessed data for $0.004/GB. Ideal for backups and archives accessed less than once per year.
              </li>
              <li>
                <strong>Custom Machine Types:</strong> Create VMs with exact vCPU and memory requirements. Save 20-40% by avoiding oversized instances.
              </li>
              <li>
                <strong>Cloud CDN:</strong> Cache content globally and reduce egress costs by 40-60%.
              </li>
              <li>
                <strong>BigQuery Flat-Rate Pricing:</strong> For heavy analytics workloads, flat-rate pricing can reduce costs by 50% compared to on-demand.
              </li>
            </ul>
          </div>

          <div className="tip-card azure-card">
            <h3>🔷 Azure Cost Optimization</h3>
            <ul>
              <li>
                <strong>Azure Hybrid Benefit:</strong> Use existing Windows Server and SQL Server licenses on Azure. Save up to 40% on VM costs.
              </li>
              <li>
                <strong>Spot VMs:</strong> Up to 90% savings for evictable workloads like batch processing, dev/test environments, and rendering.
              </li>
              <li>
                <strong>Reserved Instances:</strong> Save 72% with 3-year reservations. Can be exchanged if your needs change.
              </li>
              <li>
                <strong>Cool/Archive Blob Storage:</strong> $0.01/GB for infrequent access, $0.002/GB for archive. Automatic tiering available.
              </li>
              <li>
                <strong>Dev/Test Pricing:</strong> Get 40-60% discounts on Azure services for non-production workloads with Visual Studio subscriptions.
              </li>
              <li>
                <strong>Azure Front Door:</strong> Global load balancing and CDN in one service. Reduce data transfer costs by 50%.
              </li>
              <li>
                <strong>SQL Database Elastic Pools:</strong> Share resources across multiple databases. Save 30-50% for multi-tenant applications.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* General Strategies */}
      <div className="general-strategies">
        <h2>🌍 Universal Multi-Cloud Strategies</h2>
        <div className="strategy-grid">
          <div className="strategy-card">
            <div className="strategy-icon">🎯</div>
            <h3>Right-Sizing Resources</h3>
            <p>Monitor actual usage and downsize overprovisioned instances. Most workloads use less than 50% of allocated resources.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">30-50%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">⏰</div>
            <h3>Auto-Scheduling</h3>
            <p>Stop dev/test environments outside business hours. Running 9-5 Mon-Fri instead of 24/7 saves 65% monthly.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">60-70%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">📊</div>
            <h3>Storage Tiering</h3>
            <p>Use hot storage for frequent access, cool for monthly, archive for yearly. Automatic policies can reduce costs by 70%.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">50-80%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">🗜️</div>
            <h3>Data Compression</h3>
            <p>Enable compression for databases and file storage. Reduce storage size by 50-70% without application changes.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">50-70%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">🌐</div>
            <h3>CDN Usage</h3>
            <p>Serve static content from edge locations. Reduce origin data transfer costs by 60% and improve performance.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">40-60%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">🔄</div>
            <h3>Lifecycle Policies</h3>
            <p>Automatically transition old data to cheaper storage classes. Set delete policies for temporary data.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">40-60%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">🚀</div>
            <h3>Serverless Architecture</h3>
            <p>Use Lambda/Cloud Functions/Azure Functions for event-driven workloads. Pay only for actual execution time.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">70-90%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">📦</div>
            <h3>Containerization</h3>
            <p>Use containers instead of VMs for better resource utilization. Run 5-10x more workloads on same infrastructure.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">50-80%</span>
            </div>
          </div>

          <div className="strategy-card">
            <div className="strategy-icon">🔍</div>
            <h3>Tag Everything</h3>
            <p>Use consistent tagging for cost allocation. Identify unused resources and optimize spending by team/project.</p>
            <div className="strategy-impact">
              <span className="impact-label">Potential Savings:</span>
              <span className="impact-value">20-30%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Wins */}
      <div className="quick-wins">
        <h2>⚡ Quick Wins (Implement Today)</h2>
        <div className="wins-list">
          <div className="win-item">
            <span className="win-number">1</span>
            <div className="win-content">
              <h4>Delete Unattached Volumes</h4>
              <p>Find and delete EBS volumes, persistent disks, and managed disks not attached to any VM. Average savings: $50-500/month.</p>
            </div>
          </div>
          <div className="win-item">
            <span className="win-number">2</span>
            <div className="win-content">
              <h4>Stop Idle VMs</h4>
              <p>Identify VMs with less than 5% CPU usage over 7 days. Stop or downsize them. Average savings: $200-2000/month.</p>
            </div>
          </div>
          <div className="win-item">
            <span className="win-number">3</span>
            <div className="win-content">
              <h4>Clean Up Old Snapshots</h4>
              <p>Delete snapshots older than 90 days that aren't needed. Move others to cheaper storage. Average savings: $100-1000/month.</p>
            </div>
          </div>
          <div className="win-item">
            <span className="win-number">4</span>
            <div className="win-content">
              <h4>Remove Unused Load Balancers</h4>
              <p>Identify load balancers with zero traffic. Each idle LB costs $15-20/month. Average savings: $50-300/month.</p>
            </div>
          </div>
          <div className="win-item">
            <span className="win-number">5</span>
            <div className="win-content">
              <h4>Optimize Data Transfer</h4>
              <p>Use private network transfers instead of public internet. Keep traffic within same region/zone. Average savings: $100-500/month.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Monitoring */}
      <div className="monitoring-section">
        <h2>📊 Set Up Cost Monitoring</h2>
        <div className="monitoring-grid">
          <div className="monitoring-card">
            <h3>Budget Alerts</h3>
            <ul>
              <li>Set monthly budget thresholds at 50%, 80%, and 100%</li>
              <li>Configure email/SMS notifications</li>
              <li>Create separate budgets per project/environment</li>
            </ul>
          </div>
          <div className="monitoring-card">
            <h3>Anomaly Detection</h3>
            <ul>
              <li>Enable cloud provider anomaly detection services</li>
              <li>Set up alerts for 20%+ day-over-day cost increases</li>
              <li>Review anomalies weekly</li>
            </ul>
          </div>
          <div className="monitoring-card">
            <h3>Regular Reviews</h3>
            <ul>
              <li>Weekly: Review top 10 most expensive resources</li>
              <li>Monthly: Analyze cost trends and optimize</li>
              <li>Quarterly: Review reserved instance utilization</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CostOptimizationPage;
