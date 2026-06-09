// =============================================================================
// PAGE: StoragePage.jsx  (564 lines)
// ROUTE: /dashboard/storage
// PURPOSE: Standard (non-secure) multi-cloud file management — ML-guided placement
//          (analyze → recommendation modal → confirm), upload to AWS/GCP/Azure,
//          list files, download (access tracked), delete, Glacier restore, AWS sync
// API: Uses api.js (listFiles, getDownloadUrl, deleteFile, uploadFile, syncAwsBucket)
//      + local apiClient wrappers for analyzeFile and initiateGlacierRestore
// STATE: files, recommendation, modals for delete/restore/recommendation
// BACKEND: /api/storage/* — analyze, upload, files, download, delete, sync/*, restore/{csp}
// DO NOT:
//   - Skip the analyze → recommendation modal → confirm flow (ML prediction must be logged)
//   - Hardcode CSP — always read from file.csp or recommendation.recommendation.csp
//   - Remove access tracking in download (feeds access_frequency_score for ML tiering)
// =============================================================================
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useNotifications } from "../hooks/useNotifications";
import { TableSkeleton } from "../components/Skeletons.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  listFiles,
  getDownloadUrl,
  deleteFile,
  uploadFile as uploadFileToCSP,
  syncAwsBucket,
  syncGcpBucket,
  syncAzureContainer,
  getApiErrorMessage,
} from "../api";
import "../styles/storage.css";
import PageHeader from "../components/ui/PageHeader.jsx";
import ByocStorageTargetBanner from "../components/ByocStorageTargetBanner.jsx";
import StorageUploadWizard from "../components/StorageUploadWizard.jsx";
import CloudDestinationPanel from "../components/CloudDestinationPanel.jsx";
import StorageRegionScopeBar, {
  platformLabelForSlug,
} from "../components/StorageRegionScopeBar.jsx";
import EmptyState from "../components/EmptyState.jsx";
import CloudProviderToolbar, {
  filterFilesByCloudProvider,
} from "../components/CloudProviderSelect.jsx";
import CloudAvailabilityBanner from "../components/CloudAvailabilityBanner.jsx";
import {
  useCloudAvailability,
  buildCloudProviderOptions,
  coerceCloudProvider,
} from "../hooks/useCloudAvailability.js";
import { IconHardDrive } from "../components/dashboard/Icons.jsx";
import { usePlatformStorageRegions } from "../hooks/usePlatformStorageRegions.js";
import { usePageRefresh } from "../hooks/usePageRefresh.js";
import { minLoadingDelay } from "../utils/minLoadingDelay.js";
import { usePreferences } from "../context/PreferencesContext.jsx";

// --- API FUNCTIONS (Missing from api.js) ---
import { apiClient } from "../api";
const analyzeFile = async (data, _token) => {
  const response = await apiClient.post("/storage/analyze", data);
  return response.data;
};
const initiateArchiveRestore = async (filename, csp, tier, days, _token) => {
  const formData = new FormData();
  formData.append("tier", tier);
  formData.append("days", days);
  const provider = csp || "AWS";
  const response = await apiClient.post(
    `/storage/restore/${encodeURIComponent(provider)}/${encodeURIComponent(filename)}`,
    formData
  );
  return response.data;
};


// A helper component for rendering CSP logos
const CspIcon = ({ csp }) => {
  const icons = {
    AWS: "/images/aws.png",
    GCP: "/images/google-cloud_logo.png",
    Azure: "/images/Microsoft_Azure.png",
  };
  return <img src={icons[csp]} alt={`${csp} logo`} className="csp-icon" />;
};

const formatPercent = (value) => `${Math.round((Number(value) || 0) * 100)}%`;

const formatExpertName = (expert) => {
  const labels = {
    rule: "Rules",
    random_forest: "Random Forest",
    xgboost: "XGBoost",
  };
  return labels[expert] || expert;
};

// --- MAIN STORAGE PAGE COMPONENT ---

function StoragePage() {
  const { token } = useAuth();
  const {
    error: notifyError,
    success: notifySuccess,
    info: notifyInfo,
    showLoading,
    updateSuccess,
    updateError,
    updateInfo,
    executeWithNotification,
  } = useNotifications();
  const { loading: availLoading, getFeature, credentialMode } = useCloudAvailability();
  const storageProviders = getFeature("storage").providers || [];
  const storageToolbarOptions = useMemo(
    () => buildCloudProviderOptions(storageProviders),
    [storageProviders]
  );
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [catalogReloadToken, setCatalogReloadToken] = useState(0);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const [cloudProvider, setCloudProvider] = useState("ALL");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);

  const [userPriority, setUserPriority] = useState("balanced");
  const [userIntent, setUserIntent] = useState("active");
  const [showRecommendationModal, setShowRecommendationModal] = useState(false);

  useEffect(() => {
    if (!showRecommendationModal) return undefined;
    const onKeyDown = (e) => {
      if (e.key === "Escape") setShowRecommendationModal(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [showRecommendationModal]);
  const [recommendation, setRecommendation] = useState(null);
  const [manualCspSelection, setManualCspSelection] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [selectedBucket, setSelectedBucket] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.storage.bucket") || null;
    } catch {
      return null;
    }
  });
  const [selectedRegion, setSelectedRegion] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.storage.region") || "all";
    } catch {
      return "all";
    }
  });
  const [selectedGcpBucket, setSelectedGcpBucket] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.storage.gcp.bucket") || null;
    } catch {
      return null;
    }
  });
  const [selectedAzureContainer, setSelectedAzureContainer] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.storage.azure.container") || null;
    } catch {
      return null;
    }
  });
  const [awsBucketCount, setAwsBucketCount] = useState(null);
  const { platformRegionSlug: accountPlatformRegion } = usePreferences();
  const [sessionRegionOverride, setSessionRegionOverride] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.storage.platform_region_override") || null;
    } catch {
      return null;
    }
  });
  const {
    platformMultiRegion,
    platformRegions,
    defaultPlatformSlug,
  } = usePlatformStorageRegions({
    enabled: Boolean(token),
    reloadToken: catalogReloadToken,
  });

  const accountDefaultRegion =
    accountPlatformRegion || defaultPlatformSlug || platformRegions[0]?.slug || null;
  const platformRegionSlug = sessionRegionOverride || accountDefaultRegion;
  const isRegionSessionOverride =
    Boolean(sessionRegionOverride) && sessionRegionOverride !== accountDefaultRegion;
  const handleBucketSelect = useCallback((name, region) => {
    setSelectedBucket(name);
    if (region) setSelectedRegion(region);
  }, []);
  const handleGcpBucketSelect = useCallback((name) => {
    setSelectedGcpBucket(name);
  }, []);
  const handleAzureContainerSelect = useCallback((name) => {
    setSelectedAzureContainer(name);
  }, []);
  const handleAwsBucketsLoaded = useCallback((list) => {
    setAwsBucketCount(list?.length ?? null);
  }, []);

  const handlePlatformRegionSelect = useCallback(
    (slug) => {
      if (slug === accountDefaultRegion) {
        setSessionRegionOverride(null);
        try {
          sessionStorage.removeItem("zenith.storage.platform_region_override");
        } catch {
          /* ignore */
        }
        return;
      }
      setSessionRegionOverride(slug);
      try {
        sessionStorage.setItem("zenith.storage.platform_region_override", slug);
      } catch {
        /* ignore */
      }
    },
    [accountDefaultRegion]
  );

  const handleResetPlatformRegion = useCallback(() => {
    setSessionRegionOverride(null);
    try {
      sessionStorage.removeItem("zenith.storage.platform_region_override");
    } catch {
      /* ignore */
    }
  }, []);

  const handleRegionSelect = useCallback((region) => {
    setSelectedRegion(region);
    try {
      sessionStorage.setItem("zenith.storage.region", region);
    } catch {
      /* ignore */
    }
  }, []);

  // --- NEW STATE for Glacier Restore ---
  const [showRestoreModal, setShowRestoreModal] = useState(false);
  const [fileToRestore, setFileToRestore] = useState(null);
  const [restoreTier, setRestoreTier] = useState("Standard");
  const [restoreDays, setRestoreDays] = useState(7);
  const [isRestoring, setIsRestoring] = useState(false);


  const fetchFiles = useCallback(async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      let bucketFilter;
      let regionFilter;
      let platformSlugFilter;
      if (platformMultiRegion && platformRegionSlug) {
        platformSlugFilter = platformRegionSlug;
      } else if (cloudProvider === "AWS") {
        bucketFilter = selectedBucket || undefined;
        regionFilter = selectedRegion !== "all" ? selectedRegion : undefined;
      } else if (cloudProvider === "GCP") {
        bucketFilter = selectedGcpBucket || undefined;
      } else if (cloudProvider === "Azure") {
        bucketFilter = selectedAzureContainer || undefined;
      }
      const fileList = await listFiles(token, {
        bucket: bucketFilter,
        region: regionFilter,
        platformSlug: platformSlugFilter,
      });
      setFiles(fileList);
    } catch (error) {
      notifyError(getApiErrorMessage(error, "Failed to fetch files."));
    } finally {
      setIsLoading(false);
    }
  }, [
    token,
    notifyError,
    selectedBucket,
    selectedRegion,
    selectedGcpBucket,
    selectedAzureContainer,
    cloudProvider,
    platformMultiRegion,
    platformRegionSlug,
  ]);

  const syncStorageProvider = useCallback(
    async (csp, regionSlug) => {
      const slug = regionSlug || (platformMultiRegion ? platformRegionSlug : undefined);
      if (csp === "GCP") {
        return syncGcpBucket(token, {
          bucket: slug ? undefined : selectedGcpBucket || undefined,
          regionSlug: slug || undefined,
        });
      }
      if (csp === "Azure") {
        return syncAzureContainer(token, {
          container: slug ? undefined : selectedAzureContainer || undefined,
          regionSlug: slug || undefined,
        });
      }
      return syncAwsBucket(token, {
        bucket: slug ? undefined : selectedBucket || undefined,
        region: slug ? undefined : selectedRegion !== "all" ? selectedRegion : undefined,
        regionSlug: slug || undefined,
      });
    },
    [
      token,
      selectedBucket,
      selectedRegion,
      selectedGcpBucket,
      selectedAzureContainer,
      platformMultiRegion,
      platformRegionSlug,
    ]
  );

  const handleSyncWithBucket = async () => {
    if (!token) return;
    const targets =
      cloudProvider === "ALL" ? storageProviders : [cloudProvider];
    const regionSlugs =
      platformMultiRegion && platformRegions.length > 1
        ? platformRegions.map((r) => r.slug)
        : [platformRegionSlug].filter(Boolean);
    setIsSyncing(true);
    const loadingToastId = showLoading(
      platformMultiRegion && activeRegionLabel
        ? `Syncing storage in ${activeRegionLabel}…`
        : 'Syncing storage with cloud providers…'
    );
    try {
      let totalInserted = 0;
      let totalRemoved = 0;
      const skipped = [];

      for (const csp of targets) {
        const slugsToSync =
          platformMultiRegion && regionSlugs.length > 0 ? regionSlugs : [undefined];
        for (const slug of slugsToSync) {
          try {
            const result = await syncStorageProvider(csp, slug);
            totalInserted += result.inserted || 0;
            totalRemoved += result.removed || 0;
          } catch (error) {
            const msg = getApiErrorMessage(error, "Sync failed.");
            if (
              cloudProvider === "ALL" &&
              csp !== "AWS" &&
              /not configured|credentials/i.test(String(msg))
            ) {
              skipped.push(csp);
              continue;
            }
            if (csp !== "AWS" && /not configured|credentials/i.test(String(msg))) {
              updateInfo(
                loadingToastId,
                `${csp} sync needs BYOC or platform keys in Settings — connect your ${csp} account when ready.`
              );
              return;
            }
            throw error;
          }
        }
      }

      const removedMsg =
        totalRemoved > 0 ? ` Removed ${totalRemoved} stale record(s).` : "";
      if (cloudProvider === "ALL") {
        const skipMsg =
          skipped.length > 0
            ? ` Skipped ${skipped.join(", ")} (not configured).`
            : "";
        updateSuccess(
          loadingToastId,
          `Sync complete (all providers). Added ${totalInserted} new file(s).${removedMsg}${skipMsg}`
        );
      } else {
        updateSuccess(
          loadingToastId,
          `Sync complete (${cloudProvider}). Added ${totalInserted} new file(s).${removedMsg}`
        );
      }
      await fetchFiles();
    } catch (error) {
      updateError(loadingToastId, getApiErrorMessage(error, "Sync failed."));
    } finally {
      setIsSyncing(false);
    }
  };

  const handlePageRefresh = useCallback(async () => {
    if (!token) return;
    await runPageRefresh(
      async () => {
        const startedAt = Date.now();
        setCatalogReloadToken((t) => t + 1);
        await Promise.all([fetchFiles(), minLoadingDelay(startedAt)]);
      },
      {
        loadingMessage: 'Refreshing storage page…',
        successMessage: 'Storage page refreshed — files and cloud destinations updated.',
        getErrorMessage: (error) => getApiErrorMessage(error, 'Failed to refresh storage page.'),
      }
    );
  }, [token, fetchFiles, runPageRefresh]);

  const displayedFiles = useMemo(
    () => filterFilesByCloudProvider(files, cloudProvider),
    [files, cloudProvider]
  );

  const activeRegionLabel = useMemo(
    () => platformRegions.find((r) => r.slug === platformRegionSlug)?.label,
    [platformRegions, platformRegionSlug]
  );

  const listTitle = useMemo(() => {
    if (platformMultiRegion && activeRegionLabel) {
      return `Files in ${activeRegionLabel}`;
    }
    return "Your Files";
  }, [platformMultiRegion, activeRegionLabel]);

  const syncActionLabel = useMemo(() => {
    const regionPrefix =
      platformMultiRegion && activeRegionLabel ? `${activeRegionLabel} · ` : "";
    if (cloudProvider === "GCP") {
      return regionPrefix + (selectedGcpBucket ? `Sync ${selectedGcpBucket}` : "Sync GCP");
    }
    if (cloudProvider === "Azure") {
      return (
        regionPrefix +
        (selectedAzureContainer ? `Sync ${selectedAzureContainer}` : "Sync Azure")
      );
    }
    if (selectedBucket && cloudProvider === "AWS") {
      return regionPrefix + `Sync ${selectedBucket}`;
    }
    return regionPrefix + (cloudProvider === "ALL" ? "Sync all providers" : `Sync ${cloudProvider}`);
  }, [
    cloudProvider,
    selectedBucket,
    selectedGcpBucket,
    selectedAzureContainer,
    platformMultiRegion,
    activeRegionLabel,
  ]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  useEffect(() => {
    const next = coerceCloudProvider(cloudProvider, storageProviders);
    if (next != null && next !== cloudProvider) {
      setCloudProvider(next);
    }
  }, [storageProviders, cloudProvider]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleAnalyzeAndUpload = async () => {
    if (!selectedFile) return;
    setManualCspSelection(null);
    setIsAnalyzing(true);
    try {
      const result = await executeWithNotification(
        () =>
          analyzeFile(
            {
              filename: selectedFile.name,
              file_size_mb: selectedFile.size / (1024 * 1024),
              user_priority: userPriority,
              user_intent: userIntent,
            },
            token
          ),
        {
          loadingMessage: `Analyzing '${selectedFile.name}' for storage placement…`,
          successMessage: `Analysis complete for '${selectedFile.name}'.`,
          getErrorMessage: (error) => getApiErrorMessage(error, "Analysis failed."),
        }
      );
      setRecommendation(result);
      setShowRecommendationModal(true);
    } catch {
      /* toast already shown */
    } finally {
      setIsAnalyzing(false);
    }
  };

  const confirmAndUpload = async (overrideCsp) => {
    if (!selectedFile || !token || !recommendation) return;

    const recommended = recommendation.recommendation.csp;
    const finalCsp =
      overrideCsp ||
      manualCspSelection ||
      (storageProviders.includes(recommended) ? recommended : storageProviders[0]);
    if (!finalCsp || !storageProviders.includes(finalCsp)) {
      notifyError("No connected cloud provider available for upload. Connect a provider in Settings.");
      return;
    }

    const storageClass = recommendation.options_by_csp?.[finalCsp]?.service_name;
    if (!storageClass) {
      notifyError(`No storage class mapping for ${finalCsp}.`);
      return;
    }

    setShowRecommendationModal(false);
    setIsUploading(true);
    const loadingToastId = showLoading(`Uploading '${selectedFile.name}' to ${finalCsp}…`);

    try {
      const uploadBucket =
        finalCsp === "AWS"
          ? selectedBucket || undefined
          : finalCsp === "GCP"
            ? selectedGcpBucket || undefined
            : finalCsp === "Azure"
              ? selectedAzureContainer || undefined
              : undefined;
      await uploadFileToCSP(selectedFile, finalCsp, storageClass, token, {
        bucket: uploadBucket,
        regionSlug:
          platformMultiRegion && platformRegionSlug ? platformRegionSlug : undefined,
      });
      updateSuccess(
        loadingToastId,
        `'${selectedFile.name}' uploaded successfully to ${finalCsp}!`
      );
      setSelectedFile(null);
      setManualCspSelection(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchFiles();
    } catch (error) {
      updateError(loadingToastId, getApiErrorMessage(error, `Upload to ${finalCsp} failed.`));
    } finally {
      setIsUploading(false);
    }
  };

  const openDeleteConfirmation = (file) => {
    setFileToDelete(file);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!fileToDelete) return;
    const { filename } = fileToDelete;
    try {
      await executeWithNotification(
        async () => {
          await deleteFile(filename, token, {
            bucket: fileToDelete.cloud_bucket || selectedBucket || undefined,
            region: fileToDelete.region || undefined,
            platformSlug: fileToDelete.platform_slug || undefined,
          });
          await fetchFiles();
        },
        {
          loadingMessage: `Deleting '${filename}' from cloud storage…`,
          successMessage: `'${filename}' deleted successfully.`,
          getErrorMessage: (error) => getApiErrorMessage(error, "Failed to delete file."),
        }
      );
    } catch {
      /* toast already shown */
    } finally {
      setShowDeleteModal(false);
      setFileToDelete(null);
    }
  };

  // --- MODIFIED handleDownload to manage Glacier restores ---
  const handleDownload = async (file) => {
    const filename = typeof file === "string" ? file : file.filename;
    const bucket =
      typeof file === "object" ? file.cloud_bucket || selectedBucket : selectedBucket;
    const loadingToastId = showLoading(`Preparing download for '${filename}'…`);
    try {
      const { presigned_url } = await getDownloadUrl(filename, token, {
        bucket: bucket || undefined,
        region: typeof file === "object" ? file.region || undefined : undefined,
        platformSlug: typeof file === "object" ? file.platform_slug || undefined : undefined,
      });
      window.open(presigned_url, "_blank");
      updateSuccess(loadingToastId, `Download started for '${filename}'.`);
    } catch (error) {
      const msg = error.message || error.detail || "";
      if (msg.includes("is in GLACIER storage") && msg.includes("412")) {
        setFileToRestore(filename);
        setShowRestoreModal(true);
        updateInfo(
          loadingToastId,
          "This file is in Glacier. Restore it first, then download again."
        );
      } else if (error.message?.includes("is currently being restored") && error.message?.includes("409")) {
        updateInfo(loadingToastId, error.message);
      } else {
        updateError(loadingToastId, getApiErrorMessage(error, "Could not get download link."));
      }
    }
  };

  // --- NEW: Function to open restore modal directly (e.g., from a button in the file list) ---
  const openRestoreConfirmation = (filename) => {
    setFileToRestore(filename);
    setShowRestoreModal(true);
  };

  // --- NEW: Function to confirm and initiate Glacier restore ---
  const confirmRestore = async () => {
    if (!fileToRestore || !token) return;

    setIsRestoring(true);
    try {
      const record = files.find((f) => f.filename === fileToRestore);
      const restoreCsp = record?.csp || "AWS";
      const result = await executeWithNotification(
        async () => {
          const res = await initiateArchiveRestore(
            fileToRestore,
            restoreCsp,
            restoreTier,
            restoreDays,
            token
          );
          await fetchFiles();
          return res;
        },
        {
          loadingMessage: `Requesting ${restoreTier} restore for '${fileToRestore}'…`,
          getSuccessMessage: (res) =>
            res.message || `'${fileToRestore}' restore initiated.`,
          getErrorMessage: (error) =>
            getApiErrorMessage(error, `Failed to initiate restore for '${fileToRestore}'.`),
        }
      );
      setShowRestoreModal(false);
      setFileToRestore(null);
    } catch {
      /* toast already shown */
    } finally {
      setIsRestoring(false);
    }
  };

  const finalUploadDestination =
    manualCspSelection ||
    (recommendation &&
      (storageProviders.includes(recommendation.recommendation.csp)
        ? recommendation.recommendation.csp
        : storageProviders[0]));

  if (!availLoading && storageProviders.length === 0) {
    return (
      <div className="storage-container zenith-page-enter">
        <PageHeader
          kicker="Object storage"
          title="Standard Storage"
          subtitle="Connect a cloud provider to upload and sync files"
        />
        <CloudAvailabilityBanner
          featureLabel="storage"
          credentialMode={credentialMode}
        />
      </div>
    );
  }

  return (
    <div className="storage-container zenith-page-enter">
      <PageHeader
        kicker="Object storage"
        title="Standard Storage"
        subtitle="Upload, analyze, and sync files across your connected cloud providers"
        onRefresh={handlePageRefresh}
        refreshing={pageRefreshing}
        refreshDisabled={isLoading || isSyncing}
      />

      <div className="storage-process-info zenith-surface">
        <div className="process-step">
          <div className="process-icon analyze">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>ML-Powered Analysis</strong>
            <span>Analyzes file size, access patterns & intent</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon recommend">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Smart Recommendations</strong>
            <span>AWS, GCP, or Azure based on cost & performance</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon tier">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Intelligent Tiering</strong>
            <span>Hot → Cool → Archive based on access</span>
          </div>
        </div>

        <div className="process-step">
          <div className="process-icon save">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </div>
          <div className="process-text">
            <strong>Cost Optimization</strong>
            <span>Save up to 60% vs standard storage</span>
          </div>
        </div>
      </div>

      <div className="upload-section zenith-surface">
        <h3 className="upload-title">Intelligent File Ingestion</h3>
        <div className="upload-form">
          <div className="file-input-group">
            <input ref={fileInputRef} type="file" onChange={handleFileChange} />
          </div>

          <div className="preference-group">
            <label>My Priority:</label>
            <select
              value={userPriority}
              onChange={(e) => setUserPriority(e.target.value)}
              className={`zenith-select priority-select priority-${userPriority}`}
            >
              <option value="balanced">Balanced</option>
              <option value="cost">Prioritize Cost Savings</option>
              <option value="performance">Prioritize Performance</option>
            </select>

            <label>Intended Use:</label>
            <select
              value={userIntent}
              onChange={(e) => setUserIntent(e.target.value)}
              className={`zenith-select intent-select intent-${userIntent}`}
            >
              <option value="active">Active / Frequent</option>
              <option value="infrequent">Infrequent Access</option>
              <option value="archival">Archival</option>
            </select>
          </div>

          <button
            onClick={handleAnalyzeAndUpload}
            className="upload-btn"
            disabled={isAnalyzing || !selectedFile}
          >
            {isAnalyzing && <div className="spinner"></div>}
            {isAnalyzing ? "Analyzing..." : "Analyze & Upload"}
          </button>
        </div>
      </div>

      {platformMultiRegion && platformRegions.length > 1 && (
        <StorageRegionScopeBar
          platformRegions={platformRegions}
          selectedSlug={platformRegionSlug}
          onSelect={handlePlatformRegionSelect}
          onReset={handleResetPlatformRegion}
          accountDefaultRegion={accountDefaultRegion}
          isSessionOverride={isRegionSessionOverride}
          fileCount={files.length}
          filteredCount={displayedFiles.length}
          cloudProvider={cloudProvider}
        />
      )}

      <div className="storage-destination-panel">
        <CloudDestinationPanel
          surface="storage"
          storageKeyPrefix="zenith.storage"
          activeCsp={cloudProvider}
          storageProviders={storageProviders}
          selectedBucket={selectedBucket}
          selectedRegion={selectedRegion}
          onBucketChange={handleBucketSelect}
          onRegionChange={handleRegionSelect}
          onBucketsLoaded={handleAwsBucketsLoaded}
          selectedGcpBucket={selectedGcpBucket}
          onGcpBucketChange={handleGcpBucketSelect}
          selectedAzureContainer={selectedAzureContainer}
          onAzureContainerChange={handleAzureContainerSelect}
          platformRegionSlug={platformRegionSlug}
          onPlatformRegionChange={handlePlatformRegionSelect}
          onResetPlatformRegion={handleResetPlatformRegion}
          accountDefaultRegion={accountDefaultRegion}
          isRegionSessionOverride={isRegionSessionOverride}
          platformMultiRegion={platformMultiRegion}
          platformRegions={platformRegions}
          hidePlatformRegionSelector
          reloadToken={catalogReloadToken}
        />
        <ByocStorageTargetBanner
          variant="storage"
          selectedBucket={selectedBucket}
          selectedRegion={selectedRegion}
          selectedGcpBucket={selectedGcpBucket}
          selectedAzureContainer={selectedAzureContainer}
          bucketCount={awsBucketCount}
          activeCsp={cloudProvider}
        />
      </div>

      <div className="list-section zenith-surface">
        <div className="list-header">
          <h3 className="list-title">{listTitle}</h3>
          <CloudProviderToolbar
            provider={cloudProvider}
            onProviderChange={setCloudProvider}
            onAction={handleSyncWithBucket}
            actionLabel={syncActionLabel}
            actionBusy={isSyncing}
            selectAriaLabel="Filter and sync by cloud provider"
            providerOptions={storageToolbarOptions}
          />
        </div>
        {isLoading ? (
          <TableSkeleton rows={5} columns={5} />
        ) : displayedFiles.length === 0 ? (
          <EmptyState
            icon={<IconHardDrive aria-hidden="true" />}
            title={
              files.length === 0
                ? platformMultiRegion && activeRegionLabel
                  ? `No files in ${activeRegionLabel}`
                  : "No files yet"
                : `No ${cloudProvider === "ALL" ? "" : `${cloudProvider} `}files${
                    activeRegionLabel ? ` in ${activeRegionLabel}` : ""
                  }`
            }
            message={
              files.length === 0
                ? platformMultiRegion && activeRegionLabel
                  ? `Nothing stored in ${activeRegionLabel} yet. Upload above or switch region to view another location.`
                  : "Upload a file above to see it listed here with storage class and actions."
                : cloudProvider === "ALL"
                  ? activeRegionLabel
                    ? `No files in ${activeRegionLabel} for the current filter. Try another region or sync.`
                    : "No files match the current bucket or region filter."
                  : `No ${cloudProvider} files in ${activeRegionLabel || "this region"}. Choose All or sync ${cloudProvider}.`
            }
          />
        ) : (
          <div className="table-responsive-scroll">
          <table className="file-table">
            <thead>
              <tr>
                <th>File Name</th>
                <th>Size (KB)</th>
                <th>Upload Date</th>
                <th>Location</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedFiles.map((file) => (
                  <tr key={`${file.csp || ""}-${file.cloud_bucket || ""}-${file.region || ""}-${file.filename}`}>
                    <td>{file.filename}</td>
                    <td>{(file.size_bytes / 1024).toFixed(2)}</td>
                    <td className="date-col">
                      {new Date(file.upload_date).toLocaleString()}
                    </td>
                    <td>
                      <div className="csp-location-cell">
                        <CspIcon csp={file.csp} />
                        <span>
                          {(() => {
                            const regionLabel = platformLabelForSlug(
                              file.platform_slug,
                              platformRegions
                            );
                            return regionLabel ? (
                              <span className="platform-region-badge">{regionLabel}</span>
                            ) : null;
                          })()}
                          {file.storage_class}
                          {file.region ? ` · ${file.region}` : ""}
                        </span>
                      </div>
                    </td>
                    <td>
                      <button
                        onClick={() => handleDownload(file)}
                        className="action-btn download-btn"
                      >
                        Download
                      </button>
                      {file.csp === "AWS" &&
                       (file.storage_class === "GLACIER" || file.storage_class === "DEEP_ARCHIVE") && (
                        <button
                          onClick={() => openRestoreConfirmation(file.filename)}
                          className="action-btn restore-btn"
                          disabled={file.restore_status && file.restore_status.includes("ongoing-request=\"true\"")}
                        >
                          {file.restore_status && file.restore_status.includes("ongoing-request=\"true\"")
                           ? "Restoring..." : "Restore"}
                        </button>
                      )}
                      <button
                        onClick={() => openDeleteConfirmation(file)}
                        className="action-btn delete-btn"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {showDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <p>Are you sure you want to delete &apos;{fileToDelete?.filename}&apos;?</p>
            <div className="modal-buttons">
              <button onClick={confirmDelete} className="modal-btn danger">
                Yes, Delete
              </button>
              <button
                onClick={() => setShowDeleteModal(false)}
                className="modal-btn cancel"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {showRecommendationModal && recommendation && selectedFile && (
        <StorageUploadWizard
          file={selectedFile}
          recommendation={recommendation}
          providers={storageProviders}
          selectedBucket={selectedBucket}
          selectedRegion={selectedRegion}
          onBucketChange={handleBucketSelect}
          onRegionChange={handleRegionSelect}
          selectedGcpBucket={selectedGcpBucket}
          onGcpBucketChange={handleGcpBucketSelect}
          selectedAzureContainer={selectedAzureContainer}
          onAzureContainerChange={handleAzureContainerSelect}
          platformRegionSlug={platformRegionSlug}
          onPlatformRegionChange={handlePlatformRegionSelect}
          platformMultiRegion={platformMultiRegion}
          platformRegions={platformRegions}
          manualCsp={manualCspSelection}
          onManualCspChange={setManualCspSelection}
          isUploading={isUploading}
          onClose={() => setShowRecommendationModal(false)}
          onConfirmUpload={confirmAndUpload}
        />
      )}

      {/* --- NEW: Glacier Restore Confirmation Modal --- */}
      {showRestoreModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <p className="restore-modal-title">Restore '{fileToRestore}' from Glacier</p>
            <p className="restore-modal-text">
              This file is in archival storage. It needs to be restored before
              it can be downloaded. Restoration may take some time depending on the tier.
            </p>
            <div className="restore-options">
              <label htmlFor="restore-tier">Restoration Tier:</label>
              <select
                id="restore-tier"
                value={restoreTier}
                onChange={(e) => setRestoreTier(e.target.value)}
                className="zenith-select restore-select"
              >
                <option value="Standard">Standard (3-5 hours, lowest cost)</option>
                <option value="Bulk">Bulk (5-12 hours, very low cost for large archives)</option>
                <option value="Expedited">Expedited (1-5 minutes, higher cost)</option>
              </select>

              <label htmlFor="restore-days">Available For (Days):</label>
              <input
                type="number"
                id="restore-days"
                value={restoreDays}
                onChange={(e) => setRestoreDays(parseInt(e.target.value))}
                min="1"
                max="30"
                className="restore-input"
              />
            </div>

            <div className="modal-buttons">
              <button
                className="modal-btn cancel"
                onClick={() => setShowRestoreModal(false)}
                disabled={isRestoring}
              >
                Cancel
              </button>
              <button
                className="modal-btn confirm"
                onClick={confirmRestore}
                disabled={isRestoring}
              >
                {isRestoring ? "Initiating Restore..." : "Initiate Restore"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StoragePage;
