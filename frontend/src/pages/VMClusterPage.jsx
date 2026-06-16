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
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useNotifications } from "../hooks/useNotifications";
import { getApiErrorMessage } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useOrgContext } from "../hooks/useOrgContext.js";
import OrgResourceMeta from "../components/OrgResourceMeta.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import PageContainer from "../components/ui/PageContainer.jsx";
import Panel from "../components/ui/Panel.jsx";
import { usePageRefresh } from "../hooks/usePageRefresh.js";
import { VMClusterSkeleton } from "../components/Skeletons.jsx";
import WorkloadGuidancePanel from "../components/vm/WorkloadGuidancePanel.jsx";
import ClusterSelector from "../components/vm/ClusterSelector.jsx";
import ClusterTopologyRing from "../components/vm/ClusterTopologyRing.jsx";
import ClusterHealthCard from "../components/vm/ClusterHealthCard.jsx";
import VmConfigModal from "../components/vm/VmConfigModal.jsx";
import VmCostPreview from "../components/vm/VmCostPreview.jsx";
import {
  VM_CLUSTER_FALLBACK,
  VM_CLUSTER_SLUGS,
  formatClusterLabel,
} from "../constants/vmClusters.js";
import ZenithModal from "../components/ui/ZenithModal.jsx";
import { useConfirm } from "../context/ConfirmContext.jsx";
import {
  IconArrowRightLeft,
  IconClipboardList,
  IconDownload,
  IconPlus,
  IconServer,
  IconTrash,
} from "../components/dashboard/Icons.jsx";
import CloudProviderToolbar, {
  filterFilesByCloudProvider,
} from "../components/CloudProviderSelect.jsx";
import CloudAvailabilityBanner from "../components/CloudAvailabilityBanner.jsx";
import CloudCapabilityBanner from "../components/cloud/CloudCapabilityBanner.jsx";
import CredentialSourceBadge from "../components/cloud/CredentialSourceBadge.jsx";
import PlatformRegionPills from "../components/PlatformRegionPills.jsx";
import { usePreferences } from "../context/PreferencesContext.jsx";
import {
  useCloudAvailability,
  buildCloudProviderOptions,
  coerceCloudProvider,
} from "../hooks/useCloudAvailability.js";
import { usePlatformStorageRegions } from "../hooks/usePlatformStorageRegions.js";
import "../styles/vmcluster.css";

import { getApiBaseUrl } from '../config/apiBase.js';

const VM_API_BASE = `${getApiBaseUrl()}/vm`;

const vmFetch = (path, { token, method = 'GET', body, headers = {} } = {}) => {
  const reqHeaders = { ...headers };
  if (token && token !== 'cookie') {
    reqHeaders.Authorization = `Bearer ${token}`;
  }
  if (body && !reqHeaders['Content-Type']) {
    reqHeaders['Content-Type'] = 'application/json';
  }
  return fetch(`${VM_API_BASE}${path}`, {
    method,
    headers: reqHeaders,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  });
};

const handleApiResponse = async (response) => {
  if (!response.ok) {
    const errorBody = await response.json();
    throw new Error(errorBody.detail || `API error: ${response.status}`);
  }
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json") ? response.json() : {};
};

const analyzeWorkload = (data, token) =>
  vmFetch('/analyze-workload', { token, method: 'POST', body: data }).then(handleApiResponse);

const requestVMAssignment = (data, token) =>
  vmFetch('/request', {
    token,
    method: 'POST',
    body: { csp: data.csp || 'GCP', ...data },
  }).then(handleApiResponse);

const getAllMyAssignments = (token) =>
  vmFetch('/my-assignments', { token }).then(handleApiResponse);

const transferVM = (data, token) =>
  vmFetch('/transfer', {
    token,
    method: 'POST',
    body: { csp: data.csp || 'GCP', ...data },
  }).then(handleApiResponse);

const getVMMetrics = (vmName, token, csp = 'GCP', useRealMetrics = false) =>
  vmFetch(
    `/metrics/${encodeURIComponent(vmName)}?csp=${encodeURIComponent(csp)}&use_real=${useRealMetrics}`,
    { token },
  ).then(handleApiResponse);

const getClusterHealth = (clusterType, token, csp = 'GCP') =>
  vmFetch(
    `/admin/cluster-metrics/${clusterType}?csp=${encodeURIComponent(csp)}`,
    { token },
  ).then(handleApiResponse);

const getVmClusters = (token, csp = 'GCP') =>
  vmFetch(`/clusters?csp=${encodeURIComponent(csp)}`, { token }).then(handleApiResponse);

const getVmConfig = (vmName, token, csp = 'GCP', platformRegionSlug = null) => {
  const params = new URLSearchParams({ csp });
  if (platformRegionSlug) {
    params.set('platform_region_slug', platformRegionSlug);
  }
  return vmFetch(`/config/${encodeURIComponent(vmName)}?${params.toString()}`, { token }).then(
    handleApiResponse,
  );
};

const getRecommendations = (token, minScore = 50) =>
  vmFetch(`/admin/recommendations?min_score=${minScore}`, { token }).then(handleApiResponse);

const getVmCostEstimate = (token, { csp, vmName, clusterType, rangeOnly }) => {
  const params = new URLSearchParams({ csp: csp || 'GCP' });
  if (vmName) params.set('vm_name', vmName);
  if (clusterType) params.set('cluster_type', clusterType);
  if (rangeOnly) params.set('range_only', 'true');
  return vmFetch(`/cost-estimate?${params.toString()}`, { token }).then(handleApiResponse);
};

function VMClusterPage() {
  const { token, user } = useAuth();
  const { orgName, isAdmin } = useOrgContext();
  const { platformRegionSlug: accountPlatformRegion } = usePreferences();
  const [sessionRegionOverride, setSessionRegionOverride] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.vm.platform_region_override") || null;
    } catch {
      return null;
    }
  });
  const {
    platformMultiRegion,
    platformRegions,
    defaultPlatformSlug,
  } = usePlatformStorageRegions({ enabled: Boolean(token) });
  const accountDefaultRegion =
    accountPlatformRegion || defaultPlatformSlug || platformRegions[0]?.slug || null;
  const platformRegionSlug = sessionRegionOverride || accountDefaultRegion;
  const [showOnlyMine, setShowOnlyMine] = useState(false);
  const notifications = useNotifications();
  const { confirm } = useConfirm();
  const { executeWithNotification } = notifications;
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const {
    loading: availLoading,
    data: availData,
    getFeature,
    credentialMode,
    getLockedProviders,
    getCredentialSource,
  } = useCloudAvailability();
  const vmProviders = useMemo(() => getFeature("vm").providers || [], [getFeature]);
  const vmToolbarOptions = useMemo(
    () => buildCloudProviderOptions(vmProviders),
    [vmProviders]
  );
  const vmDefault = getFeature("vm").default || vmProviders[0] || "GCP";
  const [cloudProvider, setCloudProvider] = useState(vmDefault);
  const [, setCurrentAssignment] = useState(() => {
    try { const d = JSON.parse(sessionStorage.getItem('cache_vm_assignments')); return d?.[0] || null; } catch { return null; }
  });
  const [allAssignments, setAllAssignments] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_vm_assignments')) || []; } catch { return []; }
  });
  // Only show loading skeleton if we have NO cached data
  const [isLoading, setIsLoading] = useState(() => !sessionStorage.getItem("cache_vm_clusters"));
  const [clusterHealthMap, setClusterHealthMap] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("cache_vm_clusters")) || {};
    } catch {
      return {};
    }
  });
  const [clusterCatalog, setClusterCatalog] = useState(VM_CLUSTER_FALLBACK);
  const [selectedCluster, setSelectedCluster] = useState("general");
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
  const [vmPreference, setVmPreference] = useState("");
  const [vmPool, setVmPool] = useState(null);
  const [poolLoading, setPoolLoading] = useState(false);
  const [priorityLevel, setPriorityLevel] = useState(1);
  const [isRequesting, setIsRequesting] = useState(false);
  const [costEstimate, setCostEstimate] = useState(null);
  const [costRange, setCostRange] = useState(null);
  const [costLoading, setCostLoading] = useState(false);
  // Metrics mode toggle
  const [useRealMetrics, setUseRealMetrics] = useState(false);

  // Transfer VM Modal
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferCluster, setTransferCluster] = useState("");
  const [transferSlot, setTransferSlot] = useState("");
  const [isTransferring, setIsTransferring] = useState(false);

  // VM Config Modal
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [sshInstructions, setSshInstructions] = useState(null);
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
  const activeCsp = cloudProvider === "ALL" ? vmDefault : cloudProvider;

  const displayedAssignments = useMemo(() => {
    const withCsp = allAssignments.map((a) => ({ ...a, csp: a.csp || "GCP" }));
    const byCloud = filterFilesByCloudProvider(withCsp, cloudProvider);
    if (!isAdmin || !showOnlyMine) return byCloud;
    const me = user?.username;
    return byCloud.filter(
      (a) => (a.created_by || a.user_id) === me
    );
  }, [allAssignments, cloudProvider, isAdmin, showOnlyMine, user?.username]);

  const healthFetchInFlight = useRef(false);

  const fetchClusterHealth = useCallback(async () => {
    if (!token || healthFetchInFlight.current) return;
    healthFetchInFlight.current = true;
    try {
      const providers =
        cloudProvider === "ALL" ? vmProviders : [activeCsp];

      await Promise.all(
        providers.map(async (csp) => {
          const results = await Promise.allSettled(
            VM_CLUSTER_SLUGS.map((slug) => getClusterHealth(slug, token, csp))
          );
          setClusterHealthMap((prev) => {
            const nextMap = { ...prev };
            results.forEach((result, index) => {
              if (result.status !== "fulfilled") return;
              const slug = VM_CLUSTER_SLUGS[index];
              const payload = result.value;
              const existing = nextMap[slug];
              if (
                !existing ||
                (payload.running_vms || 0) > (existing.running_vms || 0)
              ) {
                nextMap[slug] = { ...payload, csp };
              }
            });
            sessionStorage.setItem("cache_vm_clusters", JSON.stringify(nextMap));
            return nextMap;
          });
        })
      );
    } catch (error) {
      console.error("Error fetching cluster health:", error);
    } finally {
      healthFetchInFlight.current = false;
    }
  }, [token, cloudProvider, activeCsp, vmProviders]);

  const fetchClusterCatalog = useCallback(async () => {
    if (!token) return;
    try {
      const data = await getVmClusters(token, activeCsp);
      if (data?.clusters?.length) {
        setClusterCatalog(data.clusters);
      }
    } catch (error) {
      console.error("Error fetching cluster catalog:", error);
    }
  }, [token, activeCsp]);

  useEffect(() => {
    const next = coerceCloudProvider(cloudProvider, vmProviders);
    if (next != null && next !== cloudProvider) {
      setCloudProvider(next);
    }
  }, [vmProviders, cloudProvider]);

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
      const metricsPromises = allAssignments.map((assignment) =>
        getVMMetrics(
          assignment.vm_name,
          token,
          assignment.csp || activeCsp,
          useRealMetrics
        )
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
  }, [token, allAssignments, useRealMetrics, activeCsp]);

  // Initial load, CSP changes, and 5-minute polling
  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    const loadData = async () => {
      if (!sessionStorage.getItem("cache_vm_clusters")) {
        setIsLoading(true);
      }
      await Promise.all([fetchAssignment(), fetchClusterCatalog()]);
      if (!cancelled) setIsLoading(false);
      if (!cancelled) {
        fetchClusterHealth();
        fetchRecommendations();
      }
    };

    loadData();

    const clusterInterval = setInterval(() => {
      fetchClusterHealth();
      fetchRecommendations();
    }, 300000);

    return () => {
      cancelled = true;
      clearInterval(clusterInterval);
    };
  }, [
    token,
    activeCsp,
    cloudProvider,
    fetchAssignment,
    fetchClusterCatalog,
    fetchClusterHealth,
    fetchRecommendations,
  ]);

  const selectedClusterMeta = useMemo(
    () =>
      clusterCatalog.find((c) => c.cluster_type === selectedCluster) || {
        cluster_type: selectedCluster,
        label: formatClusterLabel(selectedCluster),
      },
    [clusterCatalog, selectedCluster]
  );

  const selectedClusterHealth = clusterHealthMap[selectedCluster] || null;

  // Separate polling for VM metrics only when assigned
  useEffect(() => {
    if (!token || allAssignments.length === 0) return;

    fetchVMMetrics();
    const metricsInterval = setInterval(fetchVMMetrics, 300000); // 5 minutes
    
    return () => clearInterval(metricsInterval);
  }, [token, allAssignments, fetchVMMetrics]);

  const resolvedClusterKey = useMemo(() => {
    if (clusterPreference) return clusterPreference.toLowerCase();
    const rec = workloadAnalysis?.recommended_cluster;
    if (rec) return String(rec).toLowerCase();
    return "general";
  }, [clusterPreference, workloadAnalysis]);

  const poolSlots = useMemo(() => {
    return vmPool?.clusters?.[resolvedClusterKey]?.slots ?? [];
  }, [vmPool, resolvedClusterKey]);

  const resolvedClusterLabel = useMemo(() => {
    return (
      clusterCatalog.find((c) => c.cluster_type === resolvedClusterKey)?.label ||
      formatClusterLabel(resolvedClusterKey)
    );
  }, [resolvedClusterKey, clusterCatalog]);

  const runningVmTotal = useMemo(
    () =>
      Object.values(clusterHealthMap).reduce(
        (sum, h) => sum + (h?.running_vms || 0),
        0
      ),
    [clusterHealthMap]
  );

  const transferPoolSlots = useMemo(() => {
    if (!transferCluster) return [];
    return vmPool?.clusters?.[transferCluster.toLowerCase()]?.slots ?? [];
  }, [vmPool, transferCluster]);

  const resetRequestModalState = useCallback(() => {
    setWorkloadDescription("");
    setFollowUpAnswers({});
    setWorkloadAnalysis(null);
    setIsAnalyzingWorkload(false);
    setClusterPreference("");
    setVmPreference("");
    setPriorityLevel(1);
    setCostEstimate(null);
    setCostRange(null);
    setCostLoading(false);
  }, []);

  const handlePlatformRegionSelect = useCallback(
    (slug) => {
      if (slug === accountDefaultRegion) {
        setSessionRegionOverride(null);
        try {
          sessionStorage.removeItem("zenith.vm.platform_region_override");
        } catch {
          /* ignore */
        }
        return;
      }
      setSessionRegionOverride(slug);
      try {
        sessionStorage.setItem("zenith.vm.platform_region_override", slug);
      } catch {
        /* ignore */
      }
      setVmPreference("");
    },
    [accountDefaultRegion]
  );

  const closeRequestModal = useCallback(() => {
    setShowRequestModal(false);
    resetRequestModalState();
  }, [resetRequestModalState]);

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

  useEffect(() => {
    if (!showRequestModal || !token) return undefined;
    let cancelled = false;
    setPoolLoading(true);
    const regionQuery = platformRegionSlug
      ? `&platform_region_slug=${encodeURIComponent(platformRegionSlug)}`
      : "";
    vmFetch(`/pool?csp=${encodeURIComponent(activeCsp)}${regionQuery}`, { token })
      .then(handleApiResponse)
      .then((data) => {
        if (!cancelled) setVmPool(data);
      })
      .catch(() => {
        if (!cancelled) setVmPool(null);
      })
      .finally(() => {
        if (!cancelled) setPoolLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [showRequestModal, token, activeCsp, platformRegionSlug]);

  useEffect(() => {
    if (!showTransferModal || !token) return undefined;
    let cancelled = false;
    const regionQuery = platformRegionSlug
      ? `&platform_region_slug=${encodeURIComponent(platformRegionSlug)}`
      : "";
    vmFetch(`/pool?csp=${encodeURIComponent(activeCsp)}${regionQuery}`, { token })
      .then(handleApiResponse)
      .then((data) => {
        if (!cancelled) setVmPool(data);
      })
      .catch(() => {
        if (!cancelled) setVmPool(null);
      });
    return () => {
      cancelled = true;
    };
  }, [showTransferModal, token, activeCsp, platformRegionSlug]);

  useEffect(() => {
    if (!vmPreference) return;
    const stillValid = poolSlots.some((s) => s.vm_name === vmPreference);
    if (!stillValid) setVmPreference("");
  }, [poolSlots, vmPreference]);

  useEffect(() => {
    if (!showRequestModal || !token) {
      setCostEstimate(null);
      setCostRange(null);
      return undefined;
    }

    let cancelled = false;
    setCostLoading(true);

    const fetchCost = async () => {
      try {
        if (vmPreference) {
          const data = await getVmCostEstimate(token, {
            csp: activeCsp,
            vmName: vmPreference,
          });
          if (!cancelled) {
            setCostEstimate(data);
            setCostRange(null);
          }
        } else {
          const data = await getVmCostEstimate(token, {
            csp: activeCsp,
            clusterType: resolvedClusterKey,
            rangeOnly: true,
          });
          if (!cancelled) {
            setCostRange(data);
            setCostEstimate(null);
          }
        }
      } catch {
        if (!cancelled) {
          setCostEstimate(null);
          setCostRange(null);
        }
      } finally {
        if (!cancelled) setCostLoading(false);
      }
    };

    fetchCost();
    return () => {
      cancelled = true;
    };
  }, [
    showRequestModal,
    token,
    activeCsp,
    vmPreference,
    resolvedClusterKey,
  ]);

  const formatSlotLabel = (slot) => {
    const base =
      slot.display_name ||
      (slot.tier_label ? `${slot.tier_label} — ${slot.vm_name}` : slot.vm_name);
    const status = (slot.status || "unknown").toLowerCase();
    if (status === "running") {
      const users = slot.active_users || 0;
      return users > 0
        ? `${base} — running (${users} user${users === 1 ? "" : "s"})`
        : `${base} — running`;
    }
    if (status === "not_provisioned" || status === "unknown") {
      return `${base} — provision on request`;
    }
    return `${base} — ${status}`;
  };

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
      await executeWithNotification(
        async () => {
          const data = {
            csp: activeCsp,
            workload_description: workloadDescription,
            follow_up_answers: Object.keys(followUpAnswers).length ? followUpAnswers : null,
            cluster_preference: clusterPreference || null,
            vm_preference: vmPreference || null,
            platform_region_slug: platformRegionSlug || null,
            priority_level: priorityLevel,
          };
          const assignment = await requestVMAssignment(data, token);
          setShowRequestModal(false);
          resetRequestModalState();
          await Promise.all([fetchAssignment(), fetchClusterHealth(), fetchVMMetrics()]);
          return assignment;
        },
        {
          loadingMessage: `Provisioning VM on ${activeCsp}…`,
          getSuccessMessage: (res) => `VM assigned: ${res.vm_name}`,
          getErrorMessage: (error) =>
            getApiErrorMessage(error, "Failed to request VM"),
        }
      );
    } catch {
      /* toast already shown */
    } finally {
      setIsRequesting(false);
    }
  };

  const handleReleaseVM = async (assignmentId = null, vmName = null) => {
    const ok = await confirm({
      title: 'Release virtual machine',
      message: vmName
        ? `Release ${vmName}? This stops billing for the instance and removes your assignment.`
        : 'Release your assigned VM? This stops billing and removes your assignment.',
      confirmLabel: 'Release VM',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await executeWithNotification(
        async () => {
          const path = assignmentId
            ? `/release/${assignmentId}`
            : '/release';
          await vmFetch(path, { token, method: 'POST' }).then(handleApiResponse);
          await Promise.all([fetchAssignment(), fetchClusterHealth(), fetchVMMetrics()]);
        },
        {
          loadingMessage: vmName ? `Releasing ${vmName}…` : "Releasing VM…",
          successMessage: "VM released successfully.",
          getErrorMessage: (error) => error.message || "Failed to release VM",
        }
      );
    } catch {
      /* toast already shown — refresh so stale released assignments disappear */
      await fetchAssignment();
    }
  };

  const handleTransferVM = async () => {
    if (!transferCluster) {
      notifications.error("Please select a target cluster");
      return;
    }

    setIsTransferring(true);
    try {
      await executeWithNotification(
        async () => {
          await transferVM(
            {
              csp: activeCsp,
              target_cluster: transferCluster,
              target_vm_name: transferSlot || null,
              reason: "User-initiated migration",
            },
            token
          );
          setShowTransferModal(false);
          setTransferCluster("");
          setTransferSlot("");
          await Promise.all([fetchAssignment(), fetchClusterHealth()]);
        },
        {
          loadingMessage: `Migrating VM to ${transferCluster}…`,
          successMessage: "VM migration initiated successfully.",
          getErrorMessage: (error) => error.message || "Failed to migrate VM",
        }
      );
    } catch {
      /* toast already shown */
    } finally {
      setIsTransferring(false);
    }
  };

  const handleDownloadSSHKey = async (assignmentId) => {
    try {
      await executeWithNotification(
        async () => {
          const response = await vmFetch(`/ssh-key/${assignmentId}`, { token });
          if (!response.ok) {
            throw new Error("Failed to download SSH key");
          }
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `vm_${assignmentId}.pem`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
        },
        {
          loadingMessage: "Preparing SSH key download…",
          successMessage: "SSH key downloaded. Remember: chmod 400 your-key.pem",
          getErrorMessage: (error) => error.message || "Failed to download SSH key",
        }
      );
    } catch {
      /* toast already shown */
    }
  };

  const handleViewSSHInstructions = async (assignmentId) => {
    try {
      const response = await vmFetch(`/ssh-instructions/${assignmentId}`, { token });

      if (!response.ok) {
        throw new Error("Failed to fetch SSH instructions");
      }

      const instructions = await response.json();
      setSshInstructions(instructions);
    } catch (error) {
      notifications.error(error.message || "Failed to fetch instructions");
    }
  };

  const handleVMClick = async (vmName) => {
    try {
      const config = await getVmConfig(
        vmName,
        token,
        activeCsp,
        platformRegionSlug
      );
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

  if (isLoading || (availLoading && !availData)) {
    return <VMClusterSkeleton />;
  }

  if (vmProviders.length === 0) {
    return (
      <PageContainer className="vm-container">
        <PageHeader
          kicker="Compute"
          title="VM Cluster Management"
          subtitle="Connect AWS, Google Cloud, or Azure with VM credentials in server .env or BYOC"
        />
        <CloudAvailabilityBanner featureLabel="virtual machines" credentialMode={credentialMode} />
      </PageContainer>
    );
  }

  const handlePageRefresh = async () => {
    await runPageRefresh(
      async () => {
        await Promise.all([
          fetchClusterHealth(),
          fetchAssignment(),
          fetchVMMetrics(),
          fetchRecommendations(),
        ]);
      },
      {
        loadingMessage: 'Refreshing VM cluster page…',
        successMessage: 'VM cluster page refreshed.',
        getErrorMessage: (error) => error.message || 'Failed to refresh VM cluster page.',
      }
    );
  };

  return (
    <PageContainer className="vm-container">
      <PageHeader
        kicker="Compute"
        title="Virtual machines"
        subtitle="Provision ephemeral workloads across multi-cloud cluster pools with intelligent placement and lifecycle controls."
        onRefresh={handlePageRefresh}
        refreshing={pageRefreshing}
        className="vm-page-header"
        actions={
          <>
            <div className="vm-page-header-live live-indicator" aria-live="polite">
              <span className="live-dot" />
              <span className="live-text">Live telemetry</span>
            </div>
            <button
              className="btn-confirm vm-header-cta"
              type="button"
              onClick={() => setShowRequestModal(true)}
            >
              <IconPlus aria-hidden="true" />
              Provision instance
            </button>
          </>
        }
      />

      <CloudCapabilityBanner
        feature="vm"
        lockedProviders={getLockedProviders('vm')}
        className="vm-capability-banner"
      />

      <Panel
        title="Intelligent Workload Placement"
        description="Describe your workload in plain English. Zenith runs NLP analysis, assigns the optimal cluster pool (General, Storage, Memory, Performance, or AI/ML), and tracks live telemetry with lifecycle controls across AWS, Google Cloud, or Azure."
        className="page-card zenith-surface zenith-surface--accent-vm"
      >
        <div className="vm-process-info">
          <div className="process-step">
            <div className="process-icon nlp">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                <path d="M8 9h8M8 13h6" />
              </svg>
            </div>
            <div className="process-text">
              <strong>NLP Workload Analysis</strong>
              <span>Plain-English intent, tech stack & urgency scoring</span>
            </div>
          </div>

          <div className="process-step">
            <div className="process-icon cluster">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <rect x="2" y="2" width="8" height="8" rx="1" />
                <rect x="14" y="2" width="8" height="8" rx="1" />
                <rect x="2" y="14" width="8" height="8" rx="1" />
                <rect x="14" y="14" width="8" height="8" rx="1" />
              </svg>
            </div>
            <div className="process-text">
              <strong>Smart Cluster Assignment</strong>
              <span>Performance, Storage, Memory, or AI/ML pools</span>
            </div>
          </div>

          <div className="process-step">
            <div className="process-icon telemetry">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <div className="process-text">
              <strong>Live Telemetry</strong>
              <span>CPU, memory & health rings per instance</span>
            </div>
          </div>

          <div className="process-step">
            <div className="process-icon lifecycle">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            </div>
            <div className="process-text">
              <strong>Lifecycle Controls</strong>
              <span>Provision, release, transfer & cost preview</span>
            </div>
          </div>
        </div>
      </Panel>

      <div className="vm-cloud-toolbar-row">
        <CloudProviderToolbar
          provider={cloudProvider}
          onProviderChange={setCloudProvider}
          selectAriaLabel="VM cloud provider"
          className="vm-cloud-toolbar"
          providerOptions={vmToolbarOptions}
        />
        <CredentialSourceBadge source={getCredentialSource(cloudProvider, 'vm')} />
      </div>

      <div className="vm-summary-strip" aria-label="Compute overview">
        <div className="vm-kpi">
          <span className="vm-kpi__label">Active instances</span>
          <span className="vm-kpi__value">{displayedAssignments.length}</span>
        </div>
        <div className="vm-kpi">
          <span className="vm-kpi__label">Running pool slots</span>
          <span className="vm-kpi__value">{runningVmTotal}</span>
        </div>
        <div className="vm-kpi">
          <span className="vm-kpi__label">Cluster pools</span>
          <span className="vm-kpi__value">{clusterCatalog.length || VM_CLUSTER_SLUGS.length}</span>
        </div>
        <div className="vm-kpi">
          <span className="vm-kpi__label">Cloud provider</span>
          <span className="vm-kpi__value vm-kpi__value--text">{activeCsp}</span>
        </div>
        {platformRegionSlug && (
          <div className="vm-kpi">
            <span className="vm-kpi__label">Region</span>
            <span className="vm-kpi__value vm-kpi__value--text">
              {platformRegions.find((r) => r.slug === platformRegionSlug)?.label ||
                platformRegionSlug}
            </span>
          </div>
        )}
      </div>

      <section className="vm-panel vm-panel--topology">
        <header className="vm-panel__header">
          <div>
            <h2 className="vm-panel__title">Cluster topology</h2>
            <p className="vm-panel__desc">
              Inspect four-tier slots per cluster. Connections highlight when the pool has running instances.
            </p>
          </div>
        </header>
        <ClusterSelector
          clusters={clusterCatalog}
          selectedCluster={selectedCluster}
          onSelect={setSelectedCluster}
          className="vm-panel__tabs"
        />
        <div className="topology-container topology-container--ring">
          <ClusterTopologyRing
            clusterLabel={selectedClusterMeta.label}
            vms={selectedClusterHealth?.vms || []}
            runningVms={selectedClusterHealth?.running_vms || 0}
            slotTiers={selectedClusterMeta.slots || []}
            onVmClick={handleVMClick}
          />
        </div>
      </section>

      {/* Current Assignment Card */}
      {allAssignments.length > 0 ? (
        <section className="vm-panel">
          <header className="vm-panel__header vm-panel__header--split">
            <div>
              <h2 className="vm-panel__title">Active instances</h2>
              <p className="vm-panel__desc">
                {displayedAssignments.length} provisioned workload{displayedAssignments.length === 1 ? "" : "s"} on {activeCsp}
              </p>
            </div>
            <div className="vm-panel__actions">
              {isAdmin && orgName && (
                <label className="vm-filter-toggle">
                  <input
                    type="checkbox"
                    checked={!showOnlyMine}
                    onChange={(e) => setShowOnlyMine(!e.target.checked)}
                  />
                  Show all team resources
                </label>
              )}
              <button
                className="btn-confirm vm-header-cta vm-header-cta--secondary"
                type="button"
                onClick={() => setShowRequestModal(true)}
              >
                <IconPlus aria-hidden="true" />
                Add instance
              </button>
            </div>
          </header>

          <div className="assignments-grid">
            {displayedAssignments.map((assignment) => (
              <article key={assignment.assignment_id} className="assignment-card">
                <div className="assignment-header">
                  <div className="assignment-header__main">
                    <h3 className="assignment-card__title">{assignment.vm_name}</h3>
                    <OrgResourceMeta
                      orgName={assignment.org_id ? orgName : null}
                      createdBy={assignment.created_by || assignment.user_id}
                      currentUsername={user?.username}
                    />
                  </div>
                  <div className="assignment-actions">
                    <button
                      className="vm-btn vm-btn--ghost"
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
                      className="vm-btn vm-btn--danger"
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
                <div className="assignment-details assignment-details--grid">
                  <div className="detail-row">
                    <span className="label">IP address</span>
                    <span className="value">{assignment.vm_ip}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Cluster</span>
                    <span className={`cluster-chip cluster-chip--${assignment.cluster_type.toLowerCase()}`}>
                      {assignment.cluster_type}
                    </span>
                  </div>
                  {assignment.platform_region_slug && (
                    <div className="detail-row">
                      <span className="label">Region:</span>
                      <span className="value">
                        {platformRegions.find((r) => r.slug === assignment.platform_region_slug)
                          ?.label || assignment.platform_region_slug}
                      </span>
                    </div>
                  )}
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
                      <h4 className="vm-metrics__title">Utilization</h4>
                      {displayedAssignments[0]?.assignment_id === assignment.assignment_id && (
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
              </article>
            ))}
          </div>
        </section>
      ) : (
        <section className="vm-panel vm-panel--empty">
          <EmptyState
            icon={<IconServer aria-hidden="true" />}
            title="No active instances"
            message="Provision a workload to get started. Zenith assigns the optimal cluster and tier based on your description."
            actionLabel="Provision instance"
            onAction={() => setShowRequestModal(true)}
          />
        </section>
      )}

      <section className="vm-panel">
        <header className="vm-panel__header">
          <div>
            <h2 className="vm-panel__title">Pool health</h2>
            <p className="vm-panel__desc">
              Telemetry for the <strong>{selectedClusterMeta.label}</strong> cluster on {activeCsp}.
            </p>
          </div>
        </header>
        <ClusterHealthCard
          health={selectedClusterHealth}
          clusterLabel={selectedClusterMeta.label}
          getCPUColor={getCPUColor}
        />
      </section>

      {/* AI Recommendations */}
      {recommendations.length > 0 && (
        <section className="vm-panel">
          <header className="vm-panel__header">
            <div>
              <h2 className="vm-panel__title">Migration recommendations</h2>
              <p className="vm-panel__desc">
                Suggested moves based on utilization patterns and cluster capacity.
              </p>
            </div>
          </header>
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
        </section>
      )}

      <ZenithModal
        open={showRequestModal}
        onClose={closeRequestModal}
        title="Request VM"
        subtitle="Describe your workload, pick a cluster and optional slot — Zenith provisions only while you need it."
        titleId="vm-request-modal-title"
        wide
        footer={
          <>
            <button className="btn-cancel" type="button" onClick={closeRequestModal}>
              Cancel
            </button>
            <button
              className="btn-confirm"
              type="button"
              onClick={handleRequestVM}
              disabled={isRequesting || !workloadDescription.trim()}
            >
              {isRequesting ? "Provisioning…" : "Provision VM"}
            </button>
          </>
        }
      >
        <form
          className="vm-request-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleRequestVM();
          }}
        >
          {vmPool?.ephemeral !== false && (
            <p className="vm-request-ephemeral-note" role="note">
              <strong>On-demand VMs:</strong> Instances are terminated when you release them
              (no idle disk charges). A fresh VM is created on your next request.
            </p>
          )}

          <section className="vm-request-section" aria-labelledby="vm-request-workload-heading">
            <h3 id="vm-request-workload-heading" className="vm-request-section__title">
              <span className="vm-request-section__step">1</span>
              Workload
            </h3>
            <div className="form-group">
              <label htmlFor="vm-workload-description">What will you run?</label>
              <textarea
                id="vm-workload-description"
                value={workloadDescription}
                onChange={(e) => setWorkloadDescription(e.target.value)}
                placeholder="e.g. PostgreSQL database ~500GB, nightly backups, 50 concurrent users"
                rows={3}
              />
            </div>
            <WorkloadGuidancePanel
              analysis={workloadAnalysis}
              isAnalyzing={isAnalyzingWorkload}
              followUpAnswers={followUpAnswers}
              onFollowUpChange={handleFollowUpChange}
              idleHint="Describe your workload — we'll score readiness and suggest a cluster."
            />
          </section>

          <section className="vm-request-section" aria-labelledby="vm-request-placement-heading">
            <h3 id="vm-request-placement-heading" className="vm-request-section__title">
              <span className="vm-request-section__step">2</span>
              Placement
            </h3>
            {platformMultiRegion && platformRegions.length > 1 && (
              <div className="vm-request-region-block">
                <PlatformRegionPills
                  regions={platformRegions}
                  selectedSlug={platformRegionSlug}
                  onSelect={handlePlatformRegionSelect}
                  id="vm-request-region"
                  rowLabel="Region"
                />
                {vmPool?.compute_target && (
                  <p className="vm-request-field-hint vm-request-region-target">
                    VMs on <strong>{activeCsp}</strong> deploy to{" "}
                    <strong>{vmPool.compute_target}</strong>
                    {vmPool.platform_region_label
                      ? ` (${vmPool.platform_region_label})`
                      : ""}
                    .
                  </p>
                )}
              </div>
            )}
            <div className="vm-request-form__row vm-request-form__row--triple">
              <div className="form-group">
                <label htmlFor="vm-cluster-preference">Cluster</label>
                <select
                  id="vm-cluster-preference"
                  className="zenith-select"
                  value={clusterPreference}
                  onChange={(e) => {
                    setClusterPreference(e.target.value);
                    setVmPreference("");
                  }}
                >
                  <option value="">
                    {workloadAnalysis?.recommended_cluster
                      ? `Auto — ${workloadAnalysis.recommended_cluster} recommended`
                      : "Auto-recommend"}
                  </option>
                  {clusterCatalog.map((cluster) => (
                    <option key={cluster.cluster_type} value={cluster.cluster_type.toUpperCase()}>
                      {cluster.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="vm-slot-preference">VM slot (optional)</label>
                <select
                  id="vm-slot-preference"
                  className="zenith-select"
                  value={vmPreference}
                  onChange={(e) => setVmPreference(e.target.value)}
                  disabled={poolLoading || poolSlots.length === 0}
                >
                  <option value="">
                    {poolLoading
                      ? "Loading slots…"
                      : "Auto — least loaded / provision"}
                  </option>
                  {poolSlots.map((slot) => (
                    <option key={slot.vm_name} value={slot.vm_name}>
                      {formatSlotLabel(slot)}
                    </option>
                  ))}
                </select>
                <span className="vm-request-field-hint">
                  Pick a named slot in the {resolvedClusterLabel} pool on {activeCsp}
                  {platformRegionSlug
                    ? ` (${platformRegions.find((r) => r.slug === platformRegionSlug)?.label || platformRegionSlug})`
                    : ""}
                  .
                </span>
              </div>
              <div className="form-group">
                <label htmlFor="vm-priority-level">Priority</label>
                <select
                  id="vm-priority-level"
                  className="zenith-select"
                  value={priorityLevel}
                  onChange={(e) => setPriorityLevel(Number(e.target.value))}
                >
                  <option value={1}>High</option>
                  <option value={2}>Normal</option>
                  <option value={3}>Low</option>
                </select>
              </div>
            </div>
          </section>

          <section
            className="vm-request-section vm-request-cost-section"
            aria-labelledby="vm-request-cost-heading"
          >
            <h3 id="vm-request-cost-heading" className="vm-request-section__title">
              <span className="vm-request-section__step">3</span>
              Cost overview
            </h3>
            <VmCostPreview
              estimate={costEstimate}
              range={costRange}
              loading={costLoading}
            />
          </section>
        </form>
      </ZenithModal>

      <ZenithModal
        open={showTransferModal}
        onClose={() => setShowTransferModal(false)}
        title="Migrate to another cluster"
        subtitle="Moves your VM to a different cluster. Brief downtime may occur."
        titleId="vm-transfer-modal-title"
        footer={
          <>
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
              disabled={isTransferring || !transferCluster}
            >
              {isTransferring ? "Migrating…" : "Migrate now"}
            </button>
          </>
        }
      >
        <div className="vm-request-form">
          <div className="form-group">
            <label htmlFor="vm-transfer-cluster">Target cluster</label>
            <select
              id="vm-transfer-cluster"
              className="zenith-select"
              value={transferCluster}
              onChange={(e) => {
                setTransferCluster(e.target.value);
                setTransferSlot("");
              }}
            >
              <option value="">Select cluster</option>
              {clusterCatalog.map((cluster) => (
                <option key={cluster.cluster_type} value={cluster.cluster_type.toUpperCase()}>
                  {cluster.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="vm-transfer-slot">Target slot (optional)</label>
            <select
              id="vm-transfer-slot"
              className="zenith-select"
              value={transferSlot}
              onChange={(e) => setTransferSlot(e.target.value)}
              disabled={!transferCluster || transferPoolSlots.length === 0}
            >
              <option value="">Auto — least loaded in cluster</option>
              {transferPoolSlots.map((slot) => (
                <option key={slot.vm_name} value={slot.vm_name}>
                  {formatSlotLabel(slot)}
                </option>
              ))}
            </select>
          </div>
          <p className="modal-note">
            Your workload will be transferred to the{" "}
            {transferSlot ? "selected slot" : "least-loaded VM"} in the target cluster on{" "}
            {activeCsp}
            {platformRegionSlug
              ? ` (${platformRegions.find((r) => r.slug === platformRegionSlug)?.label || platformRegionSlug})`
              : ""}
            . The source VM will be stopped if no other users remain.
          </p>
        </div>
      </ZenithModal>

      <ZenithModal
        open={Boolean(sshInstructions)}
        onClose={() => setSshInstructions(null)}
        title="SSH connection"
        subtitle={sshInstructions ? `${sshInstructions.vm_name} · ${sshInstructions.vm_ip}` : ''}
        footer={
          <button type="button" className="btn-confirm" onClick={() => setSshInstructions(null)}>
            Done
          </button>
        }
      >
        {sshInstructions ? (
          <div className="vm-ssh-instructions">
            <p>
              <strong>Username:</strong> {sshInstructions.ssh_username}
            </p>
            <ol className="vm-ssh-steps">
              {(sshInstructions.steps || []).map((step) => (
                <li key={step.step}>
                  <strong>{step.title}</strong>
                  {step.command ? <code>{step.command}</code> : null}
                  <span>{step.description}</span>
                </li>
              ))}
            </ol>
            {(sshInstructions.troubleshooting || []).length > 0 ? (
              <div className="vm-ssh-troubleshooting">
                <h4>Troubleshooting</h4>
                <ul>
                  {sshInstructions.troubleshooting.map((item) => (
                    <li key={item.issue}>
                      <strong>{item.issue}</strong> — {item.solution}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </ZenithModal>

      <VmConfigModal
        open={showConfigModal && Boolean(selectedVMConfig)}
        config={selectedVMConfig}
        onClose={() => setShowConfigModal(false)}
      />
    </PageContainer>
  );
}

export default VMClusterPage;
