// =============================================================================
// PAGE: VMClusterPage.jsx  (1238 lines)
// ROUTE: /dashboard/vmcluster
// PURPOSE: VM lifecycle management — NLP workload analysis, VM request (cluster assignment),
//          release, transfer/migration, real-time metrics, cluster health dashboard,
//          migration recommendations, SSH key download
// API: Uses raw fetch() via local helpers (not api.js) — intentional pattern for VM page
//      Hits /api/vm/* endpoints directly with Authorization header
// STATE: allAssignments, clusterHealth, recommendations, vmMetrics (all sessionStorage cached)
//        Modals: showRequestModal, showTransferModal, showConfigModal
// BACKEND: /api/vm/* — request, release, clusters, assignment, analyze-workload,
//          migrate, transfer, my-assignments, metrics, config
// DO NOT:
//   - Change the five cluster types: GENERAL, STORAGE, MEMORY, PERFORMANCE, AI_ML
//   - Bypass NLP workload analysis before VM request — it drives cluster assignment
//   - Remove sessionStorage caching (cache_vm_*) — prevents flicker on re-navigation
//   - Change raw fetch() to api.js — intentional VM-page API pattern
// =============================================================================
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNotifications } from "../hooks/useNotifications";
import { useAuth } from "../context/AuthContext.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import { VMClusterSkeleton } from "../components/Skeletons.jsx";
import WorkloadGuidancePanel from "../components/vm/WorkloadGuidancePanel.jsx";
import {
  IconArrowRightLeft,
  IconClipboardList,
  IconDownload,
  IconHardDrive,
  IconPlus,
  IconServer,
  IconTrash,
} from "../components/dashboard/Icons.jsx";
import "../styles/vmcluster.css";

// API Functions
const API_BASE_URL = import.meta.env.DEV 
  ? 'http://localhost:8000/api/vm'
  : 'https://zenith-backend-707i.onrender.com/api/vm';

const handleApiResponse = async (response) => {
  if (!response.ok) {
    const errorBody = await response.json();
    throw new Error(errorBody.detail || `API error: ${response.status}`);
  }
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json") ? response.json() : {};
};

const analyzeWorkload = (data, token) =>
  fetch(`${API_BASE_URL}/analyze-workload`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  }).then(handleApiResponse);

const requestVMAssignment = (data, token) =>
  fetch(`${API_BASE_URL}/request`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  }).then(handleApiResponse);

const getAllMyAssignments = (token) =>
  fetch(`${API_BASE_URL}/my-assignments`, {
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
  const notifications = useNotifications();
  const [, setCurrentAssignment] = useState(() => {
    try { const d = JSON.parse(sessionStorage.getItem('cache_vm_assignments')); return d?.[0] || null; } catch { return null; }
  });
  const [allAssignments, setAllAssignments] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_vm_assignments')) || []; } catch { return []; }
  });
  // Only show loading skeleton if we have NO cached data
  const [isLoading, setIsLoading] = useState(() => !sessionStorage.getItem('cache_vm_clusterGeneral'));
  const [generalClusterHealth, setGeneralClusterHealth] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_vm_clusterGeneral')) || null; } catch { return null; }
  });
  const [storageClusterHealth, setStorageClusterHealth] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_vm_clusterStorage')) || null; } catch { return null; }
  });
  const [recommendations, setRecommendations] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_vm_recs')) || []; } catch { return []; }
  });
  const [vmMetrics, setVmMetrics] = useState({});

  // Request VM Modal
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [workloadDescription, setWorkloadDescription] = useState("");
  const [followUpAnswers, setFollowUpAnswers] = useState({});
  const [workloadAnalysis, setWorkloadAnalysis] = useState(null);
  const [isAnalyzingWorkload, setIsAnalyzingWorkload] = useState(false);
  const analyzeDebounceRef = useRef(null);
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
    if (!token) {
      console.warn("No token available for fetching assignments");
      return;
    }
    try {
      const assignments = await getAllMyAssignments(token);
      setAllAssignments(assignments);
      setCurrentAssignment(assignments[0] || null);
      sessionStorage.setItem('cache_vm_assignments', JSON.stringify(assignments));
    } catch (error) {
      if (error.status === 401) {
        console.error("Authentication failed - token may be expired");
      } else if (!error.message?.includes("404")) {
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
      sessionStorage.setItem('cache_vm_clusterGeneral', JSON.stringify(general));
      sessionStorage.setItem('cache_vm_clusterStorage', JSON.stringify(storage));
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
      sessionStorage.setItem('cache_vm_recs', JSON.stringify(recs));
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
      // Only show skeleton if we have no cached data
      if (!sessionStorage.getItem('cache_vm_clusterGeneral')) {
        setIsLoading(true);
      }
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

  const resetRequestModalState = useCallback(() => {
    setWorkloadDescription("");
    setFollowUpAnswers({});
    setWorkloadAnalysis(null);
    setIsAnalyzingWorkload(false);
    setClusterPreference("");
    setPriorityLevel(1);
  }, []);

  const runWorkloadAnalysis = useCallback(async () => {
    const trimmed = workloadDescription.trim();
    if (!token || !trimmed || trimmed.length < 3) {
      setWorkloadAnalysis(null);
      return;
    }
    setIsAnalyzingWorkload(true);
    try {
      const result = await analyzeWorkload(
        {
          workload_description: trimmed,
          follow_up_answers: Object.keys(followUpAnswers).length ? followUpAnswers : null,
        },
        token
      );
      setWorkloadAnalysis(result);
    } catch (error) {
      console.error("Workload analysis failed:", error);
    } finally {
      setIsAnalyzingWorkload(false);
    }
  }, [token, workloadDescription, followUpAnswers]);

  useEffect(() => {
    if (!showRequestModal) return undefined;

    if (analyzeDebounceRef.current) {
      clearTimeout(analyzeDebounceRef.current);
    }

    const trimmed = workloadDescription.trim();
    if (trimmed.length < 3) {
      setWorkloadAnalysis(null);
      return undefined;
    }

    analyzeDebounceRef.current = setTimeout(() => {
      runWorkloadAnalysis();
    }, 500);

    return () => {
      if (analyzeDebounceRef.current) {
        clearTimeout(analyzeDebounceRef.current);
      }
    };
  }, [showRequestModal, workloadDescription, followUpAnswers, runWorkloadAnalysis]);

  const handleFollowUpChange = (questionId, value) => {
    setFollowUpAnswers((prev) => {
      const next = { ...prev };
      if (!value) {
        delete next[questionId];
      } else {
        next[questionId] = value;
      }
      return next;
    });
  };

  const handleRequestVM = async () => {
    if (!workloadDescription.trim()) {
      notifications.error("Please describe your workload");
      return;
    }

    setIsRequesting(true);
    try {
      const data = {
        workload_description: workloadDescription,
        follow_up_answers: Object.keys(followUpAnswers).length ? followUpAnswers : null,
        cluster_preference: clusterPreference || null,
        priority_level: priorityLevel,
      };
      const result = await requestVMAssignment(data, token);
      notifications.success(`VM Assigned: ${result.vm_name}`);
      setShowRequestModal(false);
      resetRequestModalState();
      
      await Promise.all([fetchAssignment(), fetchClusterHealth(), fetchVMMetrics()]);
    } catch (error) {
      notifications.error(error.message || "Failed to request VM");
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
        ? `${API_BASE_URL}/release/${assignmentId}`
        : `${API_BASE_URL}/release`;
      
      await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).then(handleApiResponse);
      
      notifications.success("VM released successfully");
      
      await Promise.all([fetchAssignment(), fetchClusterHealth(), fetchVMMetrics()]);
    } catch (error) {
      notifications.error(error.message || "Failed to release VM");
    }
  };

  const handleTransferVM = async () => {
    if (!transferCluster) {
      notifications.error("Please select a target cluster");
      return;
    }

    setIsTransferring(true);
    try {
      const data = {
        target_cluster: transferCluster,
        reason: "User-initiated migration",
      };
      await transferVM(data, token);
      notifications.success("VM migration initiated successfully");
      setShowTransferModal(false);
      await Promise.all([fetchAssignment(), fetchClusterHealth()]);
    } catch (error) {
      notifications.error(error.message || "Failed to migrate VM");
    } finally {
      setIsTransferring(false);
    }
  };

  const handleDownloadSSHKey = async (assignmentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/ssh-key/${assignmentId}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("Failed to download SSH key");
      }

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vm_${assignmentId}.pem`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      notifications.success("SSH key downloaded! Remember to set permissions: chmod 400");
    } catch (error) {
      notifications.error(error.message || "Failed to download SSH key");
    }
  };

  const handleViewSSHInstructions = async (assignmentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/ssh-instructions/${assignmentId}`, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch SSH instructions");
      }

      const instructions = await response.json();
      
      // Show instructions in a modal (you can style this better)
      const instructionsText = `
SSH Connection Instructions

VM: ${instructions.vm_name}
IP: ${instructions.vm_ip}
Username: ${instructions.ssh_username}

Steps:
${instructions.steps.map((step) => `
${step.step}. ${step.title}
   ${step.command || ""}
   ${step.description}
`).join("\n")}

Troubleshooting:
${instructions.troubleshooting.map((item) => `
- ${item.issue}
  ${item.solution}
`).join("\n")}
      `.trim();

      alert(instructionsText); // Replace with a better modal in production
    } catch (error) {
      notifications.error(error.message || "Failed to fetch instructions");
    }
  };

  const handleVMClick = async (vmName) => {
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
      notifications.error("Failed to fetch VM configuration");
      console.error(error);
    }
  };

  const getCPUColor = (cpuUsage) => {
    if (cpuUsage > 70) return "var(--danger)";
    if (cpuUsage > 50) return "var(--warning)";
    return "var(--success)";
  };

  if (isLoading) {
    return <VMClusterSkeleton />;
  }

  return (
    <div className="vm-container">
      <PageHeader
        className="zenith-page-header--row"
        kicker="Compute"
        title="VM Cluster Management"
        subtitle="Intelligent workload assignment with auto-scaling and migration"
      >
        <div className="zenith-page-header-actions live-indicator">
          <span className="live-dot"></span>
          <span className="live-text">Live</span>
        </div>
      </PageHeader>

      {/* VM Process Flow */}
      <div className="vm-process-info">
        <div className="process-step">
          <div className="process-icon workload">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Workload Analysis</strong>
            <span>AI determines optimal cluster & VM specs</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon assign">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Smart Assignment</strong>
            <span>Least-loaded VM with capacity optimization</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon monitor">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Real-Time Monitoring</strong>
            <span>CPU, memory, users tracked live via GCP</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon scale">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 3 21 3 21 8"/>
              <line x1="4" y1="20" x2="21" y2="3"/>
              <polyline points="21 16 21 21 16 21"/>
              <line x1="15" y1="15" x2="21" y2="21"/>
              <line x1="4" y1="4" x2="9" y2="9"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Auto Migration</strong>
            <span>Seamless transfers between clusters</span>
          </div>
        </div>
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
              type="button"
              onClick={() => setShowRequestModal(true)}
              title="Request another VM"
              aria-label="Request another virtual machine"
            >
              <IconPlus aria-hidden="true" />
              Request Another VM
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
                      type="button"
                      onClick={() => {
                        setCurrentAssignment(assignment);
                        setShowTransferModal(true);
                      }}
                      title="Migrate this VM"
                      aria-label={`Migrate VM ${assignment.vm_name}`}
                    >
                      <IconArrowRightLeft aria-hidden="true" />
                      Migrate
                    </button>
                    <button 
                      className="btn-release" 
                      type="button"
                      onClick={() => handleReleaseVM(assignment.assignment_id, assignment.vm_name)}
                      title="Release this VM"
                      aria-label={`Release VM ${assignment.vm_name}`}
                    >
                      <IconTrash aria-hidden="true" />
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
                      ssh -i ~/.ssh/vm_{assignment.assignment_id}.pem vmuser@{assignment.vm_ip}
                    </code>
                  </div>
                  <div className="detail-row ssh-key-download">
                    <button 
                      className="btn-download-key"
                      type="button"
                      onClick={() => handleDownloadSSHKey(assignment.assignment_id)}
                      title="Download SSH private key to connect to this VM"
                      aria-label={`Download SSH key for ${assignment.vm_name}`}
                    >
                      <IconDownload aria-hidden="true" />
                      Download SSH Key
                    </button>
                    <button 
                      className="btn-ssh-instructions"
                      type="button"
                      onClick={() => handleViewSSHInstructions(assignment.assignment_id)}
                      title="View detailed connection instructions"
                      aria-label={`View SSH instructions for ${assignment.vm_name}`}
                    >
                      <IconClipboardList aria-hidden="true" />
                      Instructions
                    </button>
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
        <EmptyState
          icon={<IconServer aria-hidden="true" />}
          title="No Active VM Assignment"
          message="Request a VM to get started with your workload. Choose from General or Storage clusters based on your needs."
          actionLabel="Request VM"
          onAction={() => setShowRequestModal(true)}
        />
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
        <div
          className="modal-overlay"
          onClick={() => {
            setShowRequestModal(false);
            resetRequestModalState();
          }}
        >
          <div className="modal-content modal-content--wide" onClick={(e) => e.stopPropagation()}>
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
              <WorkloadGuidancePanel
                analysis={workloadAnalysis}
                isAnalyzing={isAnalyzingWorkload}
                followUpAnswers={followUpAnswers}
                onFollowUpChange={handleFollowUpChange}
              />
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
                type="button"
                onClick={() => {
                  setShowRequestModal(false);
                  resetRequestModalState();
                }}
              >
                Cancel
              </button>
              <button
                className="btn-confirm"
                type="button"
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
                type="button"
                onClick={() => setShowTransferModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn-confirm"
                type="button"
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
                    <span className="disk-icon"><IconHardDrive aria-hidden="true" /></span>
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
                type="button"
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
