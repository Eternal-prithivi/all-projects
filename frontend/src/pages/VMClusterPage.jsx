import React, { useState, useEffect, useCallback, useRef } from "react";
import { toast, ToastContainer } from "react-toastify";
import { useAuth } from "../context/AuthContext.jsx";
import "../styles/vmcluster.css";

// API Functions
const API_BASE_URL = "http://localhost:8000/api/vm";

const handleApiResponse = async (response) => {
  if (!response.ok) {
    const errorBody = await response.json();
    throw new Error(errorBody.detail || `API error: ${response.status}`);
  }
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json") ? response.json() : {};
};

const requestVMAssignment = (data, token) =>
  fetch(`${API_BASE_URL}/request`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  }).then(handleApiResponse);

const getMyAssignment = (token) =>
  fetch(`${API_BASE_URL}/my-assignment`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

const getAllMyAssignments = (token) =>
  fetch(`${API_BASE_URL}/my-assignments`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

const releaseVM = (token) =>
  fetch(`${API_BASE_URL}/release`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

const transferVM = (data, token) =>
  fetch(`${API_BASE_URL}/transfer`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  }).then(handleApiResponse);

const getVMMetrics = (vmName, token, useRealMetrics = false) =>
  fetch(`${API_BASE_URL}/metrics/${vmName}?use_real=${useRealMetrics}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

const getClusterHealth = (clusterType, token) =>
  fetch(`${API_BASE_URL}/admin/cluster-metrics/${clusterType}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

const getRecommendations = (token, minScore = 50) =>
  fetch(`${API_BASE_URL}/admin/recommendations?min_score=${minScore}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);

function VMClusterPage() {
  const { token } = useAuth();
  const [currentAssignment, setCurrentAssignment] = useState(null);
  const [allAssignments, setAllAssignments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [generalClusterHealth, setGeneralClusterHealth] = useState(null);
  const [storageClusterHealth, setStorageClusterHealth] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [vmMetrics, setVmMetrics] = useState({});

  // Request VM Modal
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [workloadDescription, setWorkloadDescription] = useState("");
  const [clusterPreference, setClusterPreference] = useState("");
  const [priorityLevel, setPriorityLevel] = useState(1);
  const [isRequesting, setIsRequesting] = useState(false);

  // Metrics mode toggle
  const [useRealMetrics, setUseRealMetrics] = useState(false);

  // Transfer VM Modal
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferCluster, setTransferCluster] = useState("");
  const [isTransferring, setIsTransferring] = useState(false);

  // VM Config Modal
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedVMConfig, setSelectedVMConfig] = useState(null);

  // Fetch current assignment
  const fetchAssignment = useCallback(async () => {
    if (!token) return;
    try {
      const assignments = await getAllMyAssignments(token);
      setAllAssignments(assignments);
      setCurrentAssignment(assignments[0] || null);
    } catch (error) {
      if (!error.message.includes("404")) {
        console.error("Error fetching assignments:", error);
      }
      setAllAssignments([]);
      setCurrentAssignment(null);
    }
  }, [token]);

  // Fetch cluster health
  const fetchClusterHealth = useCallback(async () => {
    if (!token) return;
    try {
      const [general, storage] = await Promise.all([
        getClusterHealth("GENERAL", token),
        getClusterHealth("STORAGE", token),
      ]);
      setGeneralClusterHealth(general);
      setStorageClusterHealth(storage);
    } catch (error) {
      console.error("Error fetching cluster health:", error);
    }
  }, [token]);

  // Fetch recommendations
  const fetchRecommendations = useCallback(async () => {
    if (!token) return;
    try {
      const recs = await getRecommendations(token);
      setRecommendations(recs);
    } catch (error) {
      console.error("Error fetching recommendations:", error);
    }
  }, [token]);

  // Fetch VM metrics for current assignment
  const fetchVMMetrics = useCallback(async () => {
    if (!token || allAssignments.length === 0) return;
    try {
      // Fetch metrics for all assigned VMs
      const metricsPromises = allAssignments.map(assignment =>
        getVMMetrics(assignment.vm_name, token, useRealMetrics)
      );
      const metricsResults = await Promise.all(metricsPromises);
      
      const newMetrics = {};
      allAssignments.forEach((assignment, index) => {
        newMetrics[assignment.vm_name] = metricsResults[index];
      });
      
      setVmMetrics(newMetrics);
    } catch (error) {
      console.error("Error fetching VM metrics:", error);
    }
  }, [token, allAssignments, useRealMetrics]);

  // Single useEffect for initial load and polling
  useEffect(() => {
    if (!token) return;

    const loadData = async () => {
      setIsLoading(true);
      await Promise.all([
        fetchAssignment(),
        fetchClusterHealth(),
        fetchRecommendations(),
      ]);
      setIsLoading(false);
    };
    
    loadData();

    // Poll cluster health every 5 minutes (reduced frequency)
    const clusterInterval = setInterval(() => {
      fetchClusterHealth();
      fetchRecommendations();
    }, 300000);

    return () => clearInterval(clusterInterval);
  }, [token, fetchAssignment, fetchClusterHealth, fetchRecommendations]);

  // Separate polling for VM metrics only when assigned
  useEffect(() => {
    if (!token || allAssignments.length === 0) return;

    fetchVMMetrics();
    const metricsInterval = setInterval(fetchVMMetrics, 300000); // 5 minutes
    
    return () => clearInterval(metricsInterval);
  }, [token, allAssignments, fetchVMMetrics]);

  const handleRequestVM = async () => {
    if (!workloadDescription.trim()) {
      toast.error("Please describe your workload");
      return;
    }

    setIsRequesting(true);
    try {
      const data = {
        workload_description: workloadDescription,
        cluster_preference: clusterPreference || null,
        priority_level: priorityLevel,
      };
      const result = await requestVMAssignment(data, token);
      toast.success(`VM Assigned: ${result.vm_name}`);
      setShowRequestModal(false);
      setWorkloadDescription("");
      setClusterPreference("");
      await Promise.all([fetchAssignment(), fetchClusterHealth()]);
    } catch (error) {
      toast.error(error.message || "Failed to request VM");
    } finally {
      setIsRequesting(false);
    }
  };

  const handleReleaseVM = async (assignmentId = null, vmName = null) => {
    const confirmMsg = vmName 
      ? `Are you sure you want to release ${vmName}?`
      : "Are you sure you want to release your VM?";
    
    if (!window.confirm(confirmMsg)) return;

    try {
      const url = assignmentId 
        ? `${API_BASE_URL}/release?assignment_id=${assignmentId}`
        : `${API_BASE_URL}/release`;
      
      await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).then(handleApiResponse);
      
      toast.success("VM released successfully");
      await Promise.all([fetchAssignment(), fetchClusterHealth()]);
    } catch (error) {
      toast.error(error.message || "Failed to release VM");
    }
  };

    const handleTransferVM = async () => {
    if (!transferCluster) {
      toast.error("Please select a target cluster");
      return;
    }

    setIsTransferring(true);
    try {
      const data = {
        target_cluster: transferCluster,
        reason: "User-initiated migration",
      };
      await transferVM(data, token);
      toast.success("VM migration initiated successfully");
      setShowTransferModal(false);
      setTransferCluster("");
      await Promise.all([fetchAssignment(), fetchClusterHealth()]);
    } catch (error) {
      toast.error(error.message || "Failed to transfer VM");
    } finally {
      setIsTransferring(false);
    }
  };

  const handleVMClick = async (vmName, clusterType) => {
    try {
      // Fetch comprehensive VM configuration
      const response = await fetch(`${API_BASE_URL}/config/${vmName}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch VM configuration');
      }
      
      const config = await response.json();
      setSelectedVMConfig(config);
      setShowConfigModal(true);
    } catch (error) {
      toast.error("Failed to fetch VM configuration");
      console.error(error);
    }
  };

  const getCPUColor = (cpuUsage) => {
    if (cpuUsage > 70) return "#dc3545";
    if (cpuUsage > 50) return "#ffc107";
    return "#28a745";
  };

  if (isLoading) {
    return (
      <div className="vm-container">
        <div className="loading-spinner">Loading VM Cluster Data...</div>
      </div>
    );
  }

  return (
    <div className="vm-container">
      <ToastContainer position="top-right" theme="dark" />

      {/* Header */}
      <div className="vm-header">
        <h2>VM Cluster Management</h2>
        <p className="vm-subtitle">
          Intelligent workload assignment with auto-scaling and migration
        </p>
      </div>

      {/* Cluster Topology - First Section */}
      <div className="cluster-topology-section">
        <h4>Cluster Topology</h4>
        <div className="topology-container">
          {/* General Cluster Visualization */}
          <div className="cluster-visual">
            <div className="cluster-label">General Cluster</div>
            <div className="vms-visual-group">
              {generalClusterHealth?.vms.map((vm, index) => (
                <div key={vm.vm_name} className="vm-visual-wrapper">
                  <div 
                    className={`vm-server ${vm.status.toLowerCase()}`}
                    onClick={() => handleVMClick(vm.vm_name, 'GENERAL')}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="server-icon">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M4 1h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm1 2v2h2V3H5zm3 0v2h2V3H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8z"/>
                      </svg>
                    </div>
                    <div className="vm-name-label">{vm.vm_name}</div>
                    <div className="vm-status-indicator">{vm.status}</div>
                  </div>
                  {index < generalClusterHealth.vms.length - 1 && (
                    <div className={`connection-wire ${generalClusterHealth.running_vms > 0 ? 'active' : 'inactive'}`}></div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Storage Cluster Visualization */}
          <div className="cluster-visual">
            <div className="cluster-label">Storage Cluster</div>
            <div className="vms-visual-group">
              {storageClusterHealth?.vms.map((vm, index) => (
                <div key={vm.vm_name} className="vm-visual-wrapper">
                  <div 
                    className={`vm-server ${vm.status.toLowerCase()}`}
                    onClick={() => handleVMClick(vm.vm_name, 'STORAGE')}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="server-icon">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M4 1h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm1 2v2h2V3H5zm3 0v2h2V3H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8zm-4 6h16a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm1 2v2h2v-2H5zm3 0v2h2v-2H8z"/>
                      </svg>
                    </div>
                    <div className="vm-name-label">{vm.vm_name}</div>
                    <div className="vm-status-indicator">{vm.status}</div>
                  </div>
                  {index < storageClusterHealth.vms.length - 1 && (
                    <div className={`connection-wire ${storageClusterHealth.running_vms > 0 ? 'active' : 'inactive'}`}></div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Current Assignment Card */}
      {allAssignments.length > 0 ? (
        <div className="assignments-section">
          <div className="section-header">
            <h3>Your Active VM Assignments ({allAssignments.length})</h3>
            <button
              className="btn-request"
              onClick={() => setShowRequestModal(true)}
              title="Request another VM"
            >
              + Request Another VM
            </button>
          </div>
          
          <div className="assignments-grid">
            {allAssignments.map((assignment, index) => (
              <div key={assignment.assignment_id} className="assignment-card">
                <div className="assignment-header">
                  <h4>VM Assignment #{index + 1}</h4>
                  <div className="assignment-actions">
                    <button
                      className="btn-transfer"
                      onClick={() => {
                        setCurrentAssignment(assignment);
                        setShowTransferModal(true);
                      }}
                      title="Migrate this VM"
                    >
                      Migrate
                    </button>
                    <button 
                      className="btn-release" 
                      onClick={() => handleReleaseVM(assignment.assignment_id, assignment.vm_name)}
                      title="Release this VM"
                    >
                      Release
                    </button>
                  </div>
                </div>
                <div className="assignment-details">
                  <div className="detail-row">
                    <span className="label">VM Name:</span>
                    <span className="value vm-name">{assignment.vm_name}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">IP Address:</span>
                    <span className="value">{assignment.vm_ip}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Cluster:</span>
                    <span className={`cluster-badge ${assignment.cluster_type.toLowerCase()}`}>
                      {assignment.cluster_type}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="label">SSH Command:</span>
                    <code className="ssh-command">
                      ssh user@{assignment.vm_ip}
                    </code>
                  </div>
                  <div className="detail-row">
                    <span className="label">Assigned:</span>
                    <span className="value">
                      {new Date(assignment.assigned_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Workload:</span>
                    <span className="value workload-text">
                      {assignment.workload_description}
                    </span>
                  </div>
                </div>

                {/* VM Metrics for this assignment */}
                {vmMetrics[assignment.vm_name] && (
                  <div className="vm-metrics">
                    <div className="section-header-with-toggle">
                      <h4>Real-Time Metrics</h4>
                      {index === 0 && (
                        <div className="metrics-toggle">
                          <label className="toggle-label">
                            <input
                              type="checkbox"
                              checked={useRealMetrics}
                              onChange={(e) => setUseRealMetrics(e.target.checked)}
                            />
                            <span className="toggle-slider"></span>
                            <span className="toggle-text">
                              {useRealMetrics ? "Real Metrics" : "Simulated Metrics"}
                            </span>
                          </label>
                        </div>
                      )}
                    </div>
                    <div className="metrics-grid">
                      <div className="metric-card">
                        <div className="metric-label">CPU Usage</div>
                        <div
                          className="metric-value"
                          style={{
                            color: getCPUColor(
                              vmMetrics[assignment.vm_name].cpu_usage
                            ),
                          }}
                        >
                          {vmMetrics[assignment.vm_name].cpu_usage.toFixed(1)}%
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Memory Usage</div>
                        <div className="metric-value">
                          {vmMetrics[assignment.vm_name].memory_usage.toFixed(1)}%
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Active Users</div>
                        <div className="metric-value">
                          {vmMetrics[assignment.vm_name].active_users}
                        </div>
                      </div>
                      <div className="metric-card">
                        <div className="metric-label">Est. Cost</div>
                        <div className="metric-value">
                          $
                          {vmMetrics[assignment.vm_name].estimated_cost_usd.toFixed(4)}
                          /hr
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="no-assignment-card">
          <h3>No Active VM Assignment</h3>
          <p>Request a VM to get started with your workload</p>
          <button
            className="btn-request-primary"
            onClick={() => setShowRequestModal(true)}
          >
            Request VM
          </button>
        </div>
      )}

      {/* Cluster Health Dashboard */}
      <div className="cluster-health-section">
        <h3>Cluster Health Dashboard</h3>

        <div className="clusters-grid">
          {/* General Cluster */}
          {generalClusterHealth && (
            <div className="cluster-card">
              <div className="cluster-header">
                <h4>General Cluster</h4>
                <span className="cluster-status running">
                  {generalClusterHealth.running_vms}/{generalClusterHealth.total_vms} Running
                </span>
              </div>
              <div className="cluster-stats">
                <div className="stat-item">
                  <span className="stat-label">Active Users:</span>
                  <span className="stat-value">
                    {generalClusterHealth.total_active_users}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Avg CPU:</span>
                  <span
                    className="stat-value"
                    style={{
                      color: getCPUColor(
                        generalClusterHealth.average_cpu_usage
                      ),
                    }}
                  >
                    {generalClusterHealth.average_cpu_usage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="vm-list">
                {generalClusterHealth.vms.map((vm) => (
                  <div key={vm.vm_name} className="vm-item">
                    <div className="vm-item-header">
                      <span className="vm-item-name">{vm.vm_name}</span>
                      <span className={`vm-status ${vm.status.toLowerCase()}`}>
                        {vm.status}
                      </span>
                    </div>
                    <div className="vm-item-stats">
                      <span>CPU: {vm.cpu_usage.toFixed(1)}%</span>
                      <span>Users: {vm.active_users}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Storage Cluster */}
          {storageClusterHealth && (
            <div className="cluster-card">
              <div className="cluster-header">
                <h4>Storage Cluster</h4>
                <span className="cluster-status running">
                  {storageClusterHealth.running_vms}/{storageClusterHealth.total_vms} Running
                </span>
              </div>
              <div className="cluster-stats">
                <div className="stat-item">
                  <span className="stat-label">Active Users:</span>
                  <span className="stat-value">
                    {storageClusterHealth.total_active_users}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Avg CPU:</span>
                  <span
                    className="stat-value"
                    style={{
                      color: getCPUColor(
                        storageClusterHealth.average_cpu_usage
                      ),
                    }}
                  >
                    {storageClusterHealth.average_cpu_usage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="vm-list">
                {storageClusterHealth.vms.map((vm) => (
                  <div key={vm.vm_name} className="vm-item">
                    <div className="vm-item-header">
                      <span className="vm-item-name">{vm.vm_name}</span>
                      <span className={`vm-status ${vm.status.toLowerCase()}`}>
                        {vm.status}
                      </span>
                    </div>
                    <div className="vm-item-stats">
                      <span>CPU: {vm.cpu_usage.toFixed(1)}%</span>
                      <span>Users: {vm.active_users}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Recommendations */}
      {recommendations.length > 0 && (
        <div className="recommendations-section">
          <h3>AI Migration Recommendations</h3>
          <div className="recommendations-list">
            {recommendations.map((rec) => (
              <div key={rec.recommendation_id} className="recommendation-card">
                <div className="rec-header">
                  <span className={`rec-score score-${Math.floor(rec.score / 20)}`}>
                    Score: {rec.score}
                  </span>
                  <span className="rec-action">{rec.action}</span>
                </div>
                <div className="rec-details">
                  <p>
                    <strong>Source:</strong> {rec.source_vm} →{" "}
                    <strong>Target:</strong> {rec.target_vm}
                  </p>
                  <div className="rec-reasons">
                    {rec.reasons.map((reason, idx) => (
                      <div key={idx} className="reason-item">
                        • {reason}
                      </div>
                    ))}
                  </div>
                  {rec.expected_improvements && (
                    <div className="rec-improvements">
                      <strong>Expected Improvements:</strong>
                      {Object.entries(rec.expected_improvements).map(
                        ([key, value]) => (
                          <span key={key} className="improvement-badge">
                            {key}: {value}
                          </span>
                        )
                      )}
                    </div>
                  )}
                </div>
                <div className="rec-footer">
                  <span className="rec-confidence">
                    Confidence: {rec.confidence}%
                  </span>
                  <span className="rec-downtime">
                    Downtime: {rec.estimated_downtime_seconds}s
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Request VM Modal */}
      {showRequestModal && (
        <div className="modal-overlay" onClick={() => setShowRequestModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Request VM Assignment</h3>
            <div className="modal-form">
              <div className="form-group">
                <label>Workload Description</label>
                <textarea
                  value={workloadDescription}
                  onChange={(e) => setWorkloadDescription(e.target.value)}
                  placeholder="Describe your workload (e.g., 'Running a PostgreSQL database with 500GB data')"
                  rows="4"
                />
              </div>
              <div className="form-group">
                <label>Cluster Preference (Optional)</label>
                <select
                  value={clusterPreference}
                  onChange={(e) => setClusterPreference(e.target.value)}
                >
                  <option value="">Auto-Recommend</option>
                  <option value="GENERAL">General Cluster</option>
                  <option value="STORAGE">Storage Cluster</option>
                </select>
              </div>
              <div className="form-group">
                <label>Priority Level</label>
                <select
                  value={priorityLevel}
                  onChange={(e) => setPriorityLevel(Number(e.target.value))}
                >
                  <option value="1">High (1)</option>
                  <option value="2">Normal (2)</option>
                  <option value="3">Low (3)</option>
                </select>
              </div>
            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowRequestModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-confirm"
                onClick={handleRequestVM}
                disabled={isRequesting}
              >
                {isRequesting ? "Requesting..." : "Request VM"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Transfer VM Modal */}
      {showTransferModal && (
        <div className="modal-overlay" onClick={() => setShowTransferModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Migrate to Another Cluster</h3>
            <div className="modal-form">
              <div className="form-group">
                <label>Target Cluster</label>
                <select
                  value={transferCluster}
                  onChange={(e) => setTransferCluster(e.target.value)}
                >
                  <option value="">Select Cluster</option>
                  <option value="GENERAL">General Cluster</option>
                  <option value="STORAGE">Storage Cluster</option>
                </select>
              </div>
              <p className="modal-note">
                Your workload will be transferred to the least-loaded VM in the
                target cluster. Source VM will be stopped if no other users
                remain.
              </p>
            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowTransferModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-confirm"
                onClick={handleTransferVM}
                disabled={isTransferring}
              >
                {isTransferring ? "Migrating..." : "Migrate Now"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VM Configuration Modal */}
      {showConfigModal && selectedVMConfig && (
        <div className="modal-overlay" onClick={() => setShowConfigModal(false)}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <h3>VM Configuration: {selectedVMConfig.vm_name}</h3>
            <div className="vm-config-details">
              
              {/* Basic Information */}
              <div className="config-section">
                <h4>Basic Information</h4>
                <div className="config-grid">
                  <div className="config-item">
                    <span className="config-label">VM Name:</span>
                    <span className="config-value">{selectedVMConfig.vm_name}</span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Status:</span>
                    <span className={`cluster-badge ${selectedVMConfig.status?.toLowerCase()}`}>
                      {selectedVMConfig.status}
                    </span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Cluster Type:</span>
                    <span className={`cluster-badge ${selectedVMConfig.cluster_type?.toLowerCase()}`}>
                      {selectedVMConfig.cluster_type}
                    </span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Zone:</span>
                    <span className="config-value">{selectedVMConfig.zone}</span>
                  </div>
                </div>
              </div>

              {/* Compute Resources */}
              <div className="config-section">
                <h4>Compute Resources</h4>
                <div className="config-grid">
                  <div className="config-item">
                    <span className="config-label">Machine Type:</span>
                    <span className="config-value">{selectedVMConfig.machine_type}</span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">CPU Cores:</span>
                    <span className="config-value">{selectedVMConfig.cpu_cores} vCPUs</span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Memory:</span>
                    <span className="config-value">{selectedVMConfig.memory_gb} GB</span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Active Users:</span>
                    <span className="config-value">{selectedVMConfig.active_users}</span>
                  </div>
                </div>
              </div>

              {/* Storage Configuration */}
              <div className="config-section">
                <h4>Storage Configuration</h4>
                <div className="config-grid">
                  <div className="config-item">
                    <span className="config-label">Total Disk:</span>
                    <span className="config-value">{selectedVMConfig.total_disk_gb} GB</span>
                  </div>
                  <div className="config-item">
                    <span className="config-label">Number of Disks:</span>
                    <span className="config-value">{selectedVMConfig.disks?.length || 0}</span>
                  </div>
                </div>
                {selectedVMConfig.disks?.map((disk, index) => (
                  <div key={index} className="disk-detail">
                    <span className="disk-icon">💾</span>
                    <span className="disk-name">{disk.name}</span>
                    <span className="disk-size">{disk.size_gb} GB</span>
                    {disk.boot && <span className="boot-badge">BOOT</span>}
                  </div>
                ))}
              </div>

              {/* Network Configuration */}
              <div className="config-section">
                <h4>Network Configuration</h4>
                {selectedVMConfig.networks?.map((network, index) => (
                  <div key={index} className="network-detail">
                    <div className="config-grid">
                      <div className="config-item">
                        <span className="config-label">Network:</span>
                        <span className="config-value">{network.network}</span>
                      </div>
                      <div className="config-item">
                        <span className="config-label">Internal IP:</span>
                        <span className="config-value">{network.internal_ip || 'N/A'}</span>
                      </div>
                      <div className="config-item">
                        <span className="config-label">External IP:</span>
                        <span className="config-value">{network.external_ip || 'None'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Current Performance Metrics */}
              {selectedVMConfig.current_metrics && (
                <div className="config-section">
                  <h4>Current Performance Metrics</h4>
                  <div className="config-grid">
                    <div className="config-item">
                      <span className="config-label">CPU Usage:</span>
                      <span className="config-value" style={{ color: getCPUColor(selectedVMConfig.current_metrics.cpu_usage) }}>
                        {selectedVMConfig.current_metrics.cpu_usage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Memory Usage:</span>
                      <span className="config-value">
                        {selectedVMConfig.current_metrics.memory_usage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Disk Used:</span>
                      <span className="config-value">
                        {selectedVMConfig.current_metrics.disk_usage_gb?.toFixed(2) || '0.00'} GB
                      </span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Network In:</span>
                      <span className="config-value">
                        {selectedVMConfig.current_metrics.network_in_mb?.toFixed(2) || '0.00'} MB
                      </span>
                    </div>
                    <div className="config-item">
                      <span className="config-label">Network Out:</span>
                      <span className="config-value">
                        {selectedVMConfig.current_metrics.network_out_mb?.toFixed(2) || '0.00'} MB
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Creation Info */}
              <div className="config-section">
                <h4>Additional Information</h4>
                <div className="config-grid">
                  <div className="config-item">
                    <span className="config-label">Created:</span>
                    <span className="config-value">
                      {selectedVMConfig.created ? new Date(selectedVMConfig.created).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowConfigModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VMClusterPage;
