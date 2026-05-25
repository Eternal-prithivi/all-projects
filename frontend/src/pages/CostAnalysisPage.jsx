import React, { useState, useEffect } from 'react';
// api.js does not export a default; it exports named exports including apiClient
// We import apiClient and use it for raw HTTP calls.
import { apiClient } from '../api.js';
import { useNotifications } from "../hooks/useNotifications";
import { useNavigate } from 'react-router-dom';
import '../styles/costanalysis.css';

// Cloud provider logos using actual image files
const ProviderLogo = ({ provider }) => {
  const logoMap = {
    'aws': '/images/aws.png',
    'gcp': '/images/google-cloud_logo.png',
    'azure': '/images/Microsoft_Azure.png'
  };

  const altMap = {
    'aws': 'Amazon Web Services',
    'gcp': 'Google Cloud Platform',
    'azure': 'Microsoft Azure'
  };

  return (
    <img 
      src={logoMap[provider]} 
      alt={altMap[provider]} 
      className="provider-logo"
    />
  );
};

const CostAnalysisPage = () => {
  const navigate = useNavigate();
  const notifications = useNotifications();
  // State management
  const [selectedProvider, setSelectedProvider] = useState('aws');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [granularity, setGranularity] = useState('DAILY');
  const [costData, setCostData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [totalCost, setTotalCost] = useState(0);
  const [costByService, setCostByService] = useState([]);

  // Set default dates (last 30 days)
  useEffect(() => {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(thirtyDaysAgo.toISOString().split('T')[0]);
  }, []);

  // Fetch cost data
  const fetchCostData = async () => {
    if (!startDate || !endDate) {
      notifications.error('Please select both start and end dates');
      return;
    }

    setLoading(true);
    try {
      let response;
      
      if (selectedProvider === 'aws') {
        // Base URL already includes /api, so we call /cost/* (avoid /api/api/* 404)
        response = await apiClient.get('/cost/aws', {
          params: {
            start_date: startDate,
            end_date: endDate,
            granularity: granularity,
            group_by_dimension: ['SERVICE']
          }
        });
      } else if (selectedProvider === 'gcp') {
        response = await apiClient.get('/cost/gcp', {
          params: {
            start_date: startDate,
            end_date: endDate
          }
        });
      } else if (selectedProvider === 'azure') {
        response = await apiClient.get('/cost/azure', {
          params: {
            start_date: startDate,
            end_date: endDate
          }
        });
      }

      setCostData(response.data);
      processCostData(response.data);
      notifications.success(`${selectedProvider.toUpperCase()} cost data loaded successfully`);
    } catch (error) {
      console.error('Error fetching cost data:', error);
      notifications.error(error.response?.data?.detail || 'Failed to fetch cost data');
      setCostData(null);
    } finally {
      setLoading(false);
    }
  };

  // Process cost data (works for AWS, GCP, Azure)
  const processCostData = (data) => {
    // Check for error/placeholder responses
    if (data?.data?.status === 'not_configured' || data?.data?.status === 'missing_config' || 
        data?.data?.status === 'missing_dependency' || data?.data?.status === 'error') {
      setTotalCost(data?.data?.estimated_cost || 0);
      setCostByService([]);
      return;
    }

    // Handle unified format (ResultsByTime for AWS/GCP/Azure)
    if (!data?.data?.ResultsByTime) {
      setTotalCost(0);
      setCostByService([]);
      return;
    }

    let total = 0;
    const serviceMap = {};

    // Process time series data
    data.data.ResultsByTime.forEach((timeRange) => {
      if (timeRange.Groups && timeRange.Groups.length > 0) {
        // AWS grouped data
        timeRange.Groups.forEach((group) => {
          const serviceName = group.Keys[0];
          const cost = parseFloat(group.Metrics.UnblendedCost.Amount);
          
          if (serviceMap[serviceName]) {
            serviceMap[serviceName] += cost;
          } else {
            serviceMap[serviceName] = cost;
          }
          total += cost;
        });
      } else {
        // Daily totals (all providers)
        const cost = parseFloat(timeRange.Total.UnblendedCost.Amount);
        total += cost;
      }
    });

    // For GCP/Azure, if Services array is provided, use it instead
    if (data?.data?.Services && data.data.Services.length > 0) {
      data.data.Services.forEach(svc => {
        serviceMap[svc.service] = svc.cost;
      });
      total = data.data.TotalCost || total;
    }

    setTotalCost(total);
    
    const serviceArray = Object.entries(serviceMap)
      .map(([service, cost]) => ({ service, cost }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10); // Top 10 services
    
    setCostByService(serviceArray);
  };  // Auto-fetch on provider/date/granularity change
  useEffect(() => {
    if (startDate && endDate) {
      fetchCostData();
    }
  }, [selectedProvider]);

  return (
    <div className="cost-analysis-container">
      <div className="cost-header">
        <div>
          <h1>Cost Analysis</h1>
          <p>Monitor and optimize your multi-cloud spending</p>
        </div>
        <div className="header-buttons">
          <button 
            className="simulator-button"
            onClick={() => navigate('/dashboard/simulator')}
          >
            💰 Cost Simulator
          </button>
          <button 
            className="optimization-button"
            onClick={() => navigate('/dashboard/optimization')}
          >
            💡 Optimization Tips
          </button>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="cost-filters">
        <div className="filter-group provider-group">
          <label>Cloud Provider</label>
          <div className="provider-select-wrapper">
            <ProviderLogo provider={selectedProvider} />
            <select 
              value={selectedProvider} 
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="filter-select with-logo"
            >
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
              <option value="azure">Azure</option>
            </select>
          </div>
        </div>

        <div className="filter-group">
          <label>Start Date</label>
          <input 
            type="date" 
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="filter-input"
          />
        </div>

        <div className="filter-group">
          <label>End Date</label>
          <input 
            type="date" 
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="filter-input"
          />
        </div>

        {selectedProvider === 'aws' && (
          <div className="filter-group">
            <label>Granularity</label>
            <select 
              value={granularity}
              onChange={(e) => setGranularity(e.target.value)}
              className="filter-select"
            >
              <option value="DAILY">Daily</option>
              <option value="MONTHLY">Monthly</option>
            </select>
          </div>
        )}

        <button 
          onClick={fetchCostData} 
          className="fetch-button"
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Fetch Costs'}
        </button>
      </div>

      {/* Cost Summary Cards */}
      {costData && (
        <>
          <div className="cost-summary">
            <div className="summary-card">
              <div className="card-icon">💰</div>
              <div className="card-content">
                <h3>Total Cost</h3>
                <p className="cost-value">${totalCost.toFixed(2)}</p>
                <span className="cost-period">
                  {startDate} to {endDate}
                </span>
              </div>
            </div>

            <div className="summary-card">
              <div className="card-icon">📊</div>
              <div className="card-content">
                <h3>Average Daily Cost</h3>
                <p className="cost-value">
                  ${(totalCost / Math.max(1, Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24)))).toFixed(2)}
                </p>
                <span className="cost-period">Per day average</span>
              </div>
            </div>

            <div className="summary-card provider-summary">
              <div className="card-icon provider-icon">
                <ProviderLogo provider={selectedProvider} />
              </div>
              <div className="card-content">
                <h3>Provider</h3>
                <p className="cost-value provider-name">{selectedProvider.toUpperCase()}</p>
                <span className="cost-period">{granularity} breakdown</span>
              </div>
            </div>

            <div className="summary-card">
              <div className="card-icon">📈</div>
              <div className="card-content">
                <h3>Services Tracked</h3>
                <p className="cost-value">{costByService.length}</p>
                <span className="cost-period">Active services</span>
              </div>
            </div>
          </div>

          {/* Cost Breakdown by Service */}
          {costByService.length > 0 && (
            <div className="cost-breakdown">
              <h2>Cost Breakdown by Service</h2>
              <div className="breakdown-table">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Cost</th>
                      <th>Percentage</th>
                      <th>Bar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {costByService.map((item, index) => (
                      <tr key={index}>
                        <td className="service-name">{item.service}</td>
                        <td className="service-cost">${item.cost.toFixed(2)}</td>
                        <td className="service-percentage">
                          {((item.cost / totalCost) * 100).toFixed(1)}%
                        </td>
                        <td className="service-bar">
                          <div className="bar-container">
                            <div 
                              className="bar-fill" 
                              style={{ width: `${(item.cost / totalCost) * 100}%` }}
                            ></div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Time Series Data */}
          {costData?.data?.ResultsByTime && (
            <div className="time-series">
              <h2>Cost Over Time</h2>
              <div className="time-series-list">
                {costData.data.ResultsByTime.map((timeRange, index) => {
                  const cost = timeRange.Total?.UnblendedCost?.Amount || '0';
                  return (
                    <div key={index} className="time-entry">
                      <span className="time-date">{timeRange.TimePeriod.Start}</span>
                      <span className="time-cost">${parseFloat(cost).toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* GCP/Azure Setup Message (when not configured) */}
          {(costData?.data?.status === 'not_configured' || costData?.data?.status === 'missing_config' || 
            costData?.data?.status === 'missing_dependency' || costData?.data?.status === 'error') && (
            <div className="provider-message">
              <h2>📊 {selectedProvider.toUpperCase()} Cost Data</h2>
              <p className="status-message">{costData?.data?.message || 'Billing integration pending'}</p>
              
              {costData?.data?.error && (
                <div className="error-note">
                  <strong>⚠️ Error:</strong> {costData.data.error}
                </div>
              )}
              
              {costData?.data?.implementation_steps && (
                <div className="feature-note">
                  <strong>Implementation Steps:</strong>
                  <ul>
                    {costData.data.implementation_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                  
                  <div className="help-links">
                    <p><strong>Quick Setup Guides:</strong></p>
                    {selectedProvider === 'gcp' && (
                      <>
                        <a href="https://cloud.google.com/billing/docs/how-to/export-data-bigquery" target="_blank" rel="noopener noreferrer">
                          → GCP BigQuery Billing Export
                        </a>
                        <a href="https://cloud.google.com/billing/docs/how-to/billing-api" target="_blank" rel="noopener noreferrer">
                          → Enable Cloud Billing API
                        </a>
                      </>
                    )}
                    {selectedProvider === 'azure' && (
                      <>
                        <a href="https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/quick-acm-cost-analysis" target="_blank" rel="noopener noreferrer">
                          → Azure Cost Management Setup
                        </a>
                        <a href="https://learn.microsoft.com/en-us/azure/cost-management-billing/automate/cost-management-api-permissions" target="_blank" rel="noopener noreferrer">
                          → Configure API Access
                        </a>
                      </>
                    )}
                  </div>
                </div>
              )}
              
              <div className="coming-soon-badge">
                <span>⚙️ Integration Status: Pending Configuration</span>
              </div>
            </div>
          )}
        </>
      )}

      {/* No Data State */}
      {!costData && !loading && (
        <div className="no-data">
          <div className="no-data-icon">📉</div>
          <h3>No Cost Data Available</h3>
          <p>Select a date range and click "Fetch Costs" to view your cloud spending</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Fetching cost data from {selectedProvider.toUpperCase()}...</p>
        </div>
      )}

      {/* Optimization Tips */}
      <div className="optimization-tips">
        <h2>💡 Cost Optimization Tips</h2>
        <div className="tips-grid">
          <div className="tip-card">
            <h3>Right-Size Resources</h3>
            <p>Analyze VM utilization and downsize overprovisioned instances to save up to 40%</p>
          </div>
          <div className="tip-card">
            <h3>Use Reserved Instances</h3>
            <p>Commit to 1-3 year terms for predictable workloads and save 30-70% on compute</p>
          </div>
          <div className="tip-card">
            <h3>Enable Auto-Scaling</h3>
            <p>Automatically adjust resources based on demand to avoid paying for idle capacity</p>
          </div>
          <div className="tip-card">
            <h3>Storage Lifecycle Policies</h3>
            <p>Move infrequently accessed data to cheaper storage tiers (Glacier, Coldline, Archive)</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CostAnalysisPage;
