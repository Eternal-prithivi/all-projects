// =============================================================================
// PAGE: CostSimulatorPage.jsx  (636 lines)
// ROUTE: /dashboard/cost-simulator
// PURPOSE: What-if cost modeling — user selects workload params, gets projected monthly
//          cost across AWS/GCP/Azure tiers with savings comparison breakdown
// API: Uses apiClient → /api/cost/simulate (POST with workload params)
// CONTEXTS: PreferencesContext (currencySymbol for all cost displays)
// DO NOT:
//   - Hardcode AWS pricing here — pricing is calculated server-side via cost/manager.py
//   - Use the simulator output as billing data — it's a read-only projection tool
//   - Remove the provider comparison table — it's the main value prop of this page
// =============================================================================
import React, { useState, useEffect } from 'react';
import { apiClient } from '../api.js';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import {
  IconChevronLeft,
  IconDatabase,
  IconDollarSign,
  IconHardDrive,
  IconServer,
  IconTarget,
} from '../components/dashboard/Icons.jsx';
import '../styles/costsimulator.css';

const ProviderLogo = ({ provider }) => {
  const logoMap = {
    'aws': '/images/aws.png',
    'gcp': '/images/google-cloud_logo.png',
    'azure': '/images/Microsoft_Azure.png'
  };

  return <img src={logoMap[provider]} alt={provider.toUpperCase()} className="provider-logo-small" />;
};

const CostSimulatorPage = () => {
  const navigate = useNavigate();
  const [serviceType, setServiceType] = useState('storage');
  const [storageSize, setStorageSize] = useState(100); // GB
  const [storageClass, setStorageClass] = useState('standard');
  const [storageRequests, setStorageRequests] = useState(10000); // API requests/month
  const [dataTransfer, setDataTransfer] = useState(50); // GB/month
  const [vmCpu, setVmCpu] = useState(2); // vCPUs
  const [vmMemory, setVmMemory] = useState(8); // GB RAM
  const [vmHours, setVmHours] = useState(730); // hours/month
  const [vmType, setVmType] = useState('general'); // general/compute/memory
  const [commitment, setCommitment] = useState('ondemand'); // ondemand/1year/3year
  const [dbSize, setDbSize] = useState(20); // GB
  const [dbType, setDbType] = useState('mysql');
  const [dbIops, setDbIops] = useState(3000); // IOPS
  const [costs, setCosts] = useState({ aws: 0, gcp: 0, azure: 0 });
  const [breakdown, setBreakdown] = useState({ 
    aws: {}, gcp: {}, azure: {} 
  });
  const [pricing, setPricing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch pricing from backend on mount
  useEffect(() => {
    const fetchPricing = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get('/pricing');
        
        // Store pricing data
        const { aws, gcp, azure, last_updated } = response.data;
        setPricing({ aws, gcp, azure });
        setLastUpdated(last_updated);
        
        toast.success('Pricing data loaded successfully');
      } catch (error) {
        console.error('Error fetching pricing:', error);
        toast.error('Failed to load pricing data');
        // Set fallback pricing if API fails
        setPricing(getFallbackPricing());
      } finally {
        setLoading(false);
      }
    };

    fetchPricing();
  }, []);

  // Fallback pricing if backend fails
  const getFallbackPricing = () => ({
    storage: {
      standard: {
        storage: { aws: 0.023, gcp: 0.020, azure: 0.018 },
        requests: { aws: 0.0004/1000, gcp: 0.0005/1000, azure: 0.0004/1000 }, // per 1k requests
        dataTransfer: { aws: 0.09, gcp: 0.12, azure: 0.087 } // per GB
      },
      infrequent: {
        storage: { aws: 0.0125, gcp: 0.010, azure: 0.010 },
        requests: { aws: 0.001/1000, gcp: 0.001/1000, azure: 0.001/1000 },
        dataTransfer: { aws: 0.09, gcp: 0.12, azure: 0.087 }
      },
      archive: {
        storage: { aws: 0.004, gcp: 0.0012, azure: 0.002 },
        requests: { aws: 0.05/1000, gcp: 0.05/1000, azure: 0.02/1000 },
        dataTransfer: { aws: 0.09, gcp: 0.12, azure: 0.087 }
      }
    },
    compute: {
      general: {
        ondemand: {
          cpu: { aws: 0.0416, gcp: 0.0475, azure: 0.040 },
          memory: { aws: 0.0052, gcp: 0.0064, azure: 0.005 }
        },
        '1year': {
          cpu: { aws: 0.0270, gcp: 0.0332, azure: 0.028 },
          memory: { aws: 0.0034, gcp: 0.0045, azure: 0.0035 }
        },
        '3year': {
          cpu: { aws: 0.0166, gcp: 0.0237, azure: 0.018 },
          memory: { aws: 0.0021, gcp: 0.0032, azure: 0.0022 }
        }
      },
      compute: { // Compute optimized
        ondemand: {
          cpu: { aws: 0.051, gcp: 0.0594, azure: 0.048 },
          memory: { aws: 0.0034, gcp: 0.0042, azure: 0.0033 }
        },
        '1year': {
          cpu: { aws: 0.0331, gcp: 0.0416, azure: 0.0336 },
          memory: { aws: 0.0022, gcp: 0.0029, azure: 0.0023 }
        },
        '3year': {
          cpu: { aws: 0.0204, gcp: 0.0297, azure: 0.0216 },
          memory: { aws: 0.0014, gcp: 0.0021, azure: 0.0015 }
        }
      },
      memory: { // Memory optimized
        ondemand: {
          cpu: { aws: 0.0532, gcp: 0.0641, azure: 0.051 },
          memory: { aws: 0.0067, gcp: 0.0086, azure: 0.0064 }
        },
        '1year': {
          cpu: { aws: 0.0346, gcp: 0.0449, azure: 0.0357 },
          memory: { aws: 0.0044, gcp: 0.0060, azure: 0.0045 }
        },
        '3year': {
          cpu: { aws: 0.0213, gcp: 0.0320, azure: 0.0229 },
          memory: { aws: 0.0027, gcp: 0.0043, azure: 0.0029 }
        }
      },
      dataTransfer: { aws: 0.09, gcp: 0.12, azure: 0.087 } // per GB egress
    },
    database: {
      mysql: {
        storage: { aws: 0.115, gcp: 0.170, azure: 0.125 }, // per GB/month
        iops: { aws: 0.10/1000, gcp: 0, azure: 0 }, // AWS charges for IOPS, GCP/Azure included
        backup: { aws: 0.095, gcp: 0.080, azure: 0.10 } // per GB/month
      },
      postgres: {
        storage: { aws: 0.115, gcp: 0.170, azure: 0.125 },
        iops: { aws: 0.10/1000, gcp: 0, azure: 0 },
        backup: { aws: 0.095, gcp: 0.080, azure: 0.10 }
      },
      mongodb: {
        storage: { aws: 0.25, gcp: 0.24, azure: 0.23 },
        iops: { aws: 0.20/1000, gcp: 0, azure: 0 },
        backup: { aws: 0.20, gcp: 0.18, azure: 0.19 }
      }
    },
    aws: {},
    gcp: {},
    azure: {}
  });

  // Calculate costs based on service type
  useEffect(() => {
    if (!pricing || !pricing.aws || !pricing.gcp || !pricing.azure) return; // Wait for pricing to load

    let newCosts = { aws: 0, gcp: 0, azure: 0 };
    let newBreakdown = { aws: {}, gcp: {}, azure: {} };

    if (serviceType === 'storage') {
      ['aws', 'gcp', 'azure'].forEach(provider => {
        const storageCost = storageSize * pricing[provider].storage[storageClass].storage;
        const requestCost = storageRequests * pricing[provider].storage[storageClass].requests;
        const transferCost = dataTransfer * pricing[provider].storage[storageClass].dataTransfer;
        
        newBreakdown[provider] = {
          storage: storageCost,
          requests: requestCost,
          transfer: transferCost
        };
        newCosts[provider] = storageCost + requestCost + transferCost;
      });
    } else if (serviceType === 'compute') {
      ['aws', 'gcp', 'azure'].forEach(provider => {
        const cpuCost = vmCpu * pricing[provider].compute[vmType][commitment].cpu * vmHours;
        const memCost = vmMemory * pricing[provider].compute[vmType][commitment].memory * vmHours;
        const transferCost = dataTransfer * pricing[provider].compute.dataTransfer;
        
        newBreakdown[provider] = {
          cpu: cpuCost,
          memory: memCost,
          transfer: transferCost,
          commitment: commitment
        };
        newCosts[provider] = cpuCost + memCost + transferCost;
      });
    } else if (serviceType === 'database') {
      ['aws', 'gcp', 'azure'].forEach(provider => {
        const storageCost = dbSize * pricing[provider].database[dbType].storage;
        const iopsCost = dbIops * pricing[provider].database[dbType].iops;
        const backupCost = dbSize * 0.5 * pricing[provider].database[dbType].backup; // 50% backup size
        
        newBreakdown[provider] = {
          storage: storageCost,
          iops: iopsCost,
          backup: backupCost
        };
        newCosts[provider] = storageCost + iopsCost + backupCost;
      });
    }

    setCosts(newCosts);
    setBreakdown(newBreakdown);
  }, [serviceType, storageSize, storageClass, storageRequests, dataTransfer, vmCpu, vmMemory, vmHours, vmType, commitment, dbSize, dbType, dbIops, pricing]);

  if (loading) {
    return (
      <div className="cost-simulator-container">
        <div className="simulator-header">
          <span className="page-kicker">Pricing Workbench</span>
          <h1>
            <span className="heading-icon"><IconDollarSign aria-hidden="true" /></span>
            Cost Simulator
          </h1>
          <p>Loading pricing data...</p>
        </div>
      </div>
    );
  }

  // Find cheapest provider
  const cheapestProvider = Object.keys(costs).reduce((a, b) => 
    costs[a] < costs[b] ? a : b
  );

  return (
    <div className="cost-simulator-container">
      <div className="simulator-header">
        <button 
          className="back-button"
          type="button"
          onClick={() => navigate('/dashboard/costs')}
        >
          <IconChevronLeft aria-hidden="true" />
          Back to Cost Analysis
        </button>
        <div>
          <span className="page-kicker">Pricing Workbench</span>
          <h1>
            <span className="heading-icon"><IconDollarSign aria-hidden="true" /></span>
            Cost Simulator
          </h1>
          <p>Compare cloud pricing across AWS, GCP, and Azure</p>
          {lastUpdated && (
            <small className="pricing-updated">
              Pricing last updated: {new Date(lastUpdated).toLocaleDateString()}
            </small>
          )}
        </div>
      </div>

      {/* Service Type Selector */}
      <div className="service-selector">
        <button 
          className={`service-btn ${serviceType === 'storage' ? 'active' : ''}`}
          type="button"
          aria-pressed={serviceType === 'storage'}
          onClick={() => setServiceType('storage')}
        >
          <IconHardDrive aria-hidden="true" />
          Storage
        </button>
        <button 
          className={`service-btn ${serviceType === 'compute' ? 'active' : ''}`}
          type="button"
          aria-pressed={serviceType === 'compute'}
          onClick={() => setServiceType('compute')}
        >
          <IconServer aria-hidden="true" />
          Compute
        </button>
        <button 
          className={`service-btn ${serviceType === 'database' ? 'active' : ''}`}
          type="button"
          aria-pressed={serviceType === 'database'}
          onClick={() => setServiceType('database')}
        >
          <IconDatabase aria-hidden="true" />
          Database
        </button>
      </div>

      {/* Configuration Panel */}
      <div className="config-panel">
        <h2>Configuration</h2>
        
        {serviceType === 'storage' && (
          <div className="config-section">
            <div className="config-item">
              <label>Storage Size: {storageSize} GB</label>
              <input 
                type="range" 
                min="1" 
                max="10000" 
                value={storageSize}
                onChange={(e) => setStorageSize(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1 GB</span>
                <span>10 TB</span>
              </div>
            </div>

            <div className="config-item">
              <label>Storage Class</label>
              <select 
                value={storageClass} 
                onChange={(e) => setStorageClass(e.target.value)}
                className="zenith-select config-select"
              >
                <option value="standard">Standard (Hot) - Frequent Access</option>
                <option value="infrequent">Infrequent Access (Cool) - Monthly Access</option>
                <option value="archive">Archive (Cold) - Yearly Access</option>
              </select>
            </div>

            <div className="config-item">
              <label>API Requests: {storageRequests.toLocaleString()}/month</label>
              <input 
                type="range" 
                min="0" 
                max="1000000" 
                step="1000"
                value={storageRequests}
                onChange={(e) => setStorageRequests(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>0</span>
                <span>1M requests</span>
              </div>
            </div>

            <div className="config-item">
              <label>Data Transfer Out: {dataTransfer} GB/month</label>
              <input 
                type="range" 
                min="0" 
                max="1000" 
                value={dataTransfer}
                onChange={(e) => setDataTransfer(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>0 GB</span>
                <span>1 TB</span>
              </div>
            </div>
          </div>
        )}

        {serviceType === 'compute' && (
          <div className="config-section">
            <div className="config-item">
              <label>Instance Type</label>
              <select 
                value={vmType} 
                onChange={(e) => setVmType(e.target.value)}
                className="zenith-select config-select"
              >
                <option value="general">General Purpose (t3/n2/D-series)</option>
                <option value="compute">Compute Optimized (c5/c2/F-series)</option>
                <option value="memory">Memory Optimized (r5/m2/E-series)</option>
              </select>
            </div>

            <div className="config-item">
              <label>Commitment</label>
              <select 
                value={commitment} 
                onChange={(e) => setCommitment(e.target.value)}
                className="zenith-select config-select"
              >
                <option value="ondemand">On-Demand (Pay as you go)</option>
                <option value="1year">1-Year Reserved (35% discount)</option>
                <option value="3year">3-Year Reserved (60% discount)</option>
              </select>
            </div>

            <div className="config-item">
              <label>vCPUs: {vmCpu}</label>
              <input 
                type="range" 
                min="1" 
                max="64" 
                value={vmCpu}
                onChange={(e) => setVmCpu(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1 vCPU</span>
                <span>64 vCPUs</span>
              </div>
            </div>

            <div className="config-item">
              <label>Memory: {vmMemory} GB</label>
              <input 
                type="range" 
                min="1" 
                max="256" 
                value={vmMemory}
                onChange={(e) => setVmMemory(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1 GB</span>
                <span>256 GB</span>
              </div>
            </div>

            <div className="config-item">
              <label>Hours per Month: {vmHours}</label>
              <input 
                type="range" 
                min="1" 
                max="730" 
                value={vmHours}
                onChange={(e) => setVmHours(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1 hr</span>
                <span>730 hrs (24/7)</span>
              </div>
            </div>

            <div className="config-item">
              <label>Data Transfer Out: {dataTransfer} GB/month</label>
              <input 
                type="range" 
                min="0" 
                max="1000" 
                value={dataTransfer}
                onChange={(e) => setDataTransfer(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>0 GB</span>
                <span>1 TB</span>
              </div>
            </div>
          </div>
        )}

        {serviceType === 'database' && (
          <div className="config-section">
            <div className="config-item">
              <label>Database Size: {dbSize} GB</label>
              <input 
                type="range" 
                min="1" 
                max="1000" 
                value={dbSize}
                onChange={(e) => setDbSize(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1 GB</span>
                <span>1 TB</span>
              </div>
            </div>

            <div className="config-item">
              <label>Database Type</label>
              <select 
                value={dbType} 
                onChange={(e) => setDbType(e.target.value)}
                className="zenith-select config-select"
              >
                <option value="mysql">MySQL (RDS/Cloud SQL/Azure DB)</option>
                <option value="postgres">PostgreSQL</option>
                <option value="mongodb">MongoDB (DocumentDB/Atlas)</option>
              </select>
            </div>

            <div className="config-item">
              <label>IOPS: {dbIops.toLocaleString()}</label>
              <input 
                type="range" 
                min="1000" 
                max="80000" 
                step="1000"
                value={dbIops}
                onChange={(e) => setDbIops(Number(e.target.value))}
                className="slider"
              />
              <div className="range-labels">
                <span>1k IOPS</span>
                <span>80k IOPS</span>
              </div>
              <small className="config-note">
                Note: AWS charges for IOPS, GCP/Azure include baseline IOPS
              </small>
            </div>
          </div>
        )}
      </div>

      {/* Price Comparison Cards */}
      <div className="comparison-grid">
        {['aws', 'gcp', 'azure'].map(provider => (
          <div 
            key={provider} 
            className={`price-card ${cheapestProvider === provider ? 'cheapest' : ''}`}
          >
            {cheapestProvider === provider && (
              <div className="best-value-badge">
                <IconTarget aria-hidden="true" />
                Best Value
              </div>
            )}
            
            <div className="card-header">
              <ProviderLogo provider={provider} />
              <h3>{provider.toUpperCase()}</h3>
            </div>

            <div className="price-amount">
              <span className="currency">$</span>
              <span className="amount">{costs[provider].toFixed(2)}</span>
              <span className="period">/month</span>
            </div>

            <div className="price-breakdown">
              {serviceType === 'storage' && (
                <>
                  <div className="breakdown-item">
                    <span>Storage ({storageSize} GB)</span>
                    <span>${breakdown[provider].storage?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>API Requests ({storageRequests.toLocaleString()})</span>
                    <span>${breakdown[provider].requests?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>Data Transfer ({dataTransfer} GB)</span>
                    <span>${breakdown[provider].transfer?.toFixed(2) || '0.00'}</span>
                  </div>
                </>
              )}

              {serviceType === 'compute' && (
                <>
                  <div className="breakdown-item">
                    <span>CPU ({vmCpu} vCPUs × {vmHours}h)</span>
                    <span>${breakdown[provider].cpu?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>Memory ({vmMemory} GB × {vmHours}h)</span>
                    <span>${breakdown[provider].memory?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>Data Transfer ({dataTransfer} GB)</span>
                    <span>${breakdown[provider].transfer?.toFixed(2) || '0.00'}</span>
                  </div>
                  {commitment !== 'ondemand' && (
                    <div className="savings-badge">
                      {commitment === '1year' ? '35%' : '60%'} discount applied
                    </div>
                  )}
                </>
              )}

              {serviceType === 'database' && (
                <>
                  <div className="breakdown-item">
                    <span>Storage ({dbSize} GB)</span>
                    <span>${breakdown[provider].storage?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>IOPS ({dbIops.toLocaleString()})</span>
                    <span>${breakdown[provider].iops?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="breakdown-item">
                    <span>Backup ({(dbSize * 0.5).toFixed(0)} GB)</span>
                    <span>${breakdown[provider].backup?.toFixed(2) || '0.00'}</span>
                  </div>
                  {breakdown[provider].iops === 0 && provider !== 'aws' && (
                    <div className="included-badge">
                      IOPS included in base price
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="savings-info">
              {cheapestProvider !== provider && (
                <span className="more-expensive">
                  +${(costs[provider] - costs[cheapestProvider]).toFixed(2)} more than {cheapestProvider.toUpperCase()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Annual Projection */}
      <div className="annual-projection">
        <h2>Annual Cost Projection</h2>
        <div className="projection-grid">
          {['aws', 'gcp', 'azure'].map(provider => (
            <div key={provider} className="projection-card">
              <ProviderLogo provider={provider} />
              <span className="provider-name">{provider.toUpperCase()}</span>
              <span className="annual-amount">${(costs[provider] * 12).toFixed(2)}/year</span>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing Notes */}
      <div className="pricing-notes">
        <h3>Pricing Notes</h3>
        <ul>
          <li>Prices are approximate and based on standard regions (US East/Central)</li>
          <li>Includes data transfer, API requests, and IOPS charges</li>
          <li>Actual costs may vary based on commitment terms and volume discounts</li>
          <li>Compute prices: General Purpose (t3/n2/D-series), Compute Optimized (c5/c2/F-series), Memory Optimized (r5/m2/E-series)</li>
          <li>Database prices are for managed services in single-AZ/zone configuration</li>
        </ul>
      </div>
    </div>
  );
};

export default CostSimulatorPage;
