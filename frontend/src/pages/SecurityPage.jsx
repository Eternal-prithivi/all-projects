// =============================================================================
// PAGE: SecurityPage.jsx  (745 lines)
// ROUTE: /dashboard/security
// PURPOSE: 2FA management (enable/disable/verify) + secure file vault
//          (upload with auto sensitive-scan, two-step encryption choice, download, delete)
// API: Uses functions from ../api.js (status2FA, enable2FA, finalize2FA, verify2FA,
//      disable2FA, listSecureFiles, deleteSecureFile, uploadSecureFile, syncAwsSecureBucket,
//      chooseEncryption, decryptAndDownload) — NOT raw fetch() — imports from api.js named exports
// STATE: twoFAStatus, secureFiles (cached in sessionStorage), encryption/decryption modals
// BACKEND: /api/2fa/*, /api/security/* (require_2fa guard — 2FA must be verified)
// DO NOT:
//   - Refactor API calls to use apiClient — these named exports from api.js are intentional
//   - Remove sessionStorage caching (cache_2faStatus, cache_secureFiles) — prevents flicker
//   - Skip the two-step upload flow (scan → choice modal → encrypt → S3)
// =============================================================================
import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useNotifications } from "../hooks/useNotifications";
import EncryptionChoiceModal from "../components/EncryptionChoiceModal";
import DecryptionPasswordModal from "../components/DecryptionPasswordModal";
import SecureUploadWizard from "../components/SecureUploadWizard";
import {
  encryptFileInBrowser,
  decryptBlobInBrowser,
  downloadBlob,
} from "../utils/clientEncryption";

import { useAuth } from "../context/AuthContext.jsx";
import {
  status2FA,
  enable2FA,
  finalize2FA,
  verify2FA,
  disable2FA,
  listSecureFiles,
  deleteSecureFile,
  getSecureDownloadUrl,
  uploadSecureFile,
  syncSecureVault,
  chooseEncryption,
  uploadClientEncrypted,
  downloadClientCiphertext,
} from "../api";
import "../styles/security-page.css";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";
import { usePageRefresh } from "../hooks/usePageRefresh.js";
import { minLoadingDelay } from "../utils/minLoadingDelay.js";
import ByocStorageTargetBanner from "../components/ByocStorageTargetBanner.jsx";
import BucketRegionSelector from "../components/BucketRegionSelector.jsx";
import CloudProviderToolbar, {
  filterFilesByCloudProvider,
} from "../components/CloudProviderSelect.jsx";
import CloudAvailabilityBanner from "../components/CloudAvailabilityBanner.jsx";
import {
  useCloudAvailability,
  buildCloudProviderOptions,
  coerceCloudProvider,
  CSP_LABELS,
} from "../hooks/useCloudAvailability.js";
import EmptyState from "../components/EmptyState.jsx";
import TwoFADialog from "../components/TwoFADialog.jsx";
import { IconLock } from "../components/dashboard/Icons.jsx";

// --- MAIN COMPONENT ---

function SecurityPage() {
  const { token, user } = useAuth();
  const notifications = useNotifications();
  const {
    executeWithNotification,
    showLoading,
    updateSuccess,
    updateError,
  } = notifications;
  const { loading: availLoading, getFeature, credentialMode } = useCloudAvailability();
  const securityProviders = getFeature("security").providers || [];
  const securityToolbarOptions = useMemo(
    () => buildCloudProviderOptions(securityProviders),
    [securityProviders]
  );
  const [file, setFile] = useState(null);
  const [encrypt, setEncrypt] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [catalogReloadToken, setCatalogReloadToken] = useState(0);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const [cloudProvider, setCloudProvider] = useState("ALL");
  const [secureFiles, setSecureFiles] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_secureFiles')) || []; } catch { return []; }
  });
  // Only show loading spinner if we have NO cached 2FA status
  const [loading, setLoading] = useState(() => !sessionStorage.getItem('cache_2faStatus'));
  const [twoFAStatus, setTwoFAStatus] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('cache_2faStatus')) || {
        enabled: false, verified: false, secret_exists: false,
      };
    } catch {
      return { enabled: false, verified: false, secret_exists: false };
    }
  });
  const [qrCode, setQrCode] = useState(null);
  const [twoFACode, setTwoFACode] = useState("");
  const [verifyPanelOpen, setVerifyPanelOpen] = useState(false);
  const [isEnabling2FA, setIsEnabling2FA] = useState(false);
  const [showDisablePanel, setShowDisablePanel] = useState(false);
  const fileInputRef = useRef(null);
  const [showModal, setShowModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(null);
  const pollIntervalRef = useRef(null);
  const [showEncryptionModal, setShowEncryptionModal] = useState(false);
  const [fileAwaitingEncryption, setFileAwaitingEncryption] = useState(null);
  const [showDecryptionModal, setShowDecryptionModal] = useState(false);
  const [fileToDecrypt, setFileToDecrypt] = useState(null);
  const [showSecureWizard, setShowSecureWizard] = useState(false);
  const [wizardSubmitting, setWizardSubmitting] = useState(false);
  const [pendingLocalFile, setPendingLocalFile] = useState(null);
  const [pendingFileMeta, setPendingFileMeta] = useState(null);
  const [alwaysAskEncryption, setAlwaysAskEncryption] = useState(() => {
    try {
      return localStorage.getItem("zenith-always-ask-encryption") === "true";
    } catch {
      return false;
    }
  });
  const [selectedBucket, setSelectedBucket] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.security.bucket") || null;
    } catch {
      return null;
    }
  });
  const [selectedRegion, setSelectedRegion] = useState(() => {
    try {
      return sessionStorage.getItem("zenith.security.region") || "all";
    } catch {
      return "all";
    }
  });
  const handleBucketSelect = (name, region) => {
    setSelectedBucket(name);
    if (region) setSelectedRegion(region);
  };

  const handleRegionSelect = (region) => {
    setSelectedRegion(region);
    try {
      sessionStorage.setItem("zenith.security.region", region);
    } catch {
      /* ignore */
    }
  };

  const canAccessSecureArea = !twoFAStatus.enabled || twoFAStatus.verified;

  const handleAlwaysAskChange = (checked) => {
    setAlwaysAskEncryption(checked);
    try {
      localStorage.setItem("zenith-always-ask-encryption", checked ? "true" : "false");
    } catch {
      /* ignore */
    }
  };

  const fetchSecureFiles = useCallback(async () => {
    if (!token || !canAccessSecureArea) return [];
    try {
      const files = await listSecureFiles(token, {
        bucket: selectedBucket || undefined,
        region: selectedRegion !== "all" ? selectedRegion : undefined,
      });
      setSecureFiles(files);
      sessionStorage.setItem('cache_secureFiles', JSON.stringify(files));
      return files;
    } catch {
      notifications.error("Could not fetch secure file list.");
      return [];
    }
  }, [token, canAccessSecureArea, selectedBucket, selectedRegion, notifications]);

  const handlePageRefresh = useCallback(async () => {
    if (!token) return;
    await runPageRefresh(
      async () => {
        const startedAt = Date.now();
        setCatalogReloadToken((t) => t + 1);
        await Promise.all([fetchSecureFiles(), minLoadingDelay(startedAt)]);
      },
      {
        loadingMessage: 'Refreshing security page…',
        successMessage: 'Security page refreshed — vault files and destinations updated.',
        getErrorMessage: (err) => err?.detail || err?.message || 'Failed to refresh security page.',
      }
    );
  }, [token, runPageRefresh, fetchSecureFiles]);

  useEffect(() => {
    const wsRef = { current: null };
    if (user && token && canAccessSecureArea && !loading) {
      fetchSecureFiles();
      const wsUrl = import.meta.env.DEV 
        ? `ws://localhost:8000/ws/status?token=${token}`
        : `wss://zenith-backend-707i.onrender.com/ws/status?token=${token}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        if (event.data === "job_complete") fetchSecureFiles();
      };
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
      // pollIntervalRef unused for scheduling today; clear if set elsewhere
      // eslint-disable-next-line react-hooks/exhaustive-deps -- ref cleanup snapshot
      const pollId = pollIntervalRef.current;
      if (pollId) clearInterval(pollId);
    };
  }, [user, token, canAccessSecureArea, fetchSecureFiles, loading]);

  useEffect(() => {
    const next = coerceCloudProvider(cloudProvider, securityProviders);
    if (next != null && next !== cloudProvider) {
      setCloudProvider(next);
    }
  }, [securityProviders, cloudProvider]);

  useEffect(() => {
    const check2FA = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await status2FA(token);
        setTwoFAStatus(res);
        sessionStorage.setItem('cache_2faStatus', JSON.stringify(res));
        if (res.enabled && !res.verified) {
          setVerifyPanelOpen(true);
        }
      } catch (err) {
        const detail = typeof err?.detail === 'string' ? err.detail : '';
        if (detail.includes('2FA token verification is required')) {
          const status = { enabled: true, verified: false, secret_exists: true };
          setTwoFAStatus(status);
          sessionStorage.setItem('cache_2faStatus', JSON.stringify(status));
          setVerifyPanelOpen(true);
        }
      } finally {
        setLoading(false);
      }
    };
    check2FA();
  }, [token]);

  const clearModalState = () => {
    setShowEncryptionModal(false);
    setShowDecryptionModal(false);
    setShowModal(false);
    setFileAwaitingEncryption(null);
    setFileToDecrypt(null);
    setPendingFileMeta(null);
  };

  const persistTwoFAStatus = (status) => {
    sessionStorage.setItem("cache_2faStatus", JSON.stringify(status));
  };

  const cancelTwoFASetup = async () => {
    try {
      if (twoFAStatus.secret_exists && !twoFAStatus.enabled) {
        await disable2FA(token);
      }
    } catch (err) {
      notifications.error(err.detail || "Could not cancel 2FA setup");
      return;
    }
    setQrCode(null);
    setTwoFACode("");
    const reset = { enabled: false, verified: false, secret_exists: false };
    setTwoFAStatus(reset);
    persistTwoFAStatus(reset);
    notifications.info("2FA setup cancelled");
  };

  const handleVerify2FA = async () => {
    try {
      const res = await verify2FA(token, twoFACode);
      if (res.verified) {
        notifications.success("2FA verified successfully!");
        setTwoFAStatus((prev) => {
          const next = { ...prev, verified: true };
          persistTwoFAStatus(next);
          return next;
        });
        setVerifyPanelOpen(false);
      }
    } catch (err) {
      notifications.error(err.detail || "Error verifying 2FA");
    }
  };

  const handleEnable2FA = async () => {
    if (!token || isEnabling2FA) return;
    setShowDisablePanel(false);
    setVerifyPanelOpen(false);
    clearModalState();
    setIsEnabling2FA(true);
    try {
      const res = await enable2FA(token);
      if (res?.qr_code) {
        setQrCode(res.qr_code);
        setTwoFACode('');
        const next = {
          secret_exists: true,
          enabled: false,
          verified: false,
        };
        setTwoFAStatus(next);
        persistTwoFAStatus(next);
      } else {
        notifications.error(res?.message || 'No QR code returned. Please try again.');
      }
    } catch (err) {
      const detail = err?.detail;
      notifications.error(
        typeof detail === 'string' ? detail : detail?.message || 'Failed to enable 2FA',
      );
    } finally {
      setIsEnabling2FA(false);
    }
  };
  const handleFinalize2FA = async () => {
    try {
      const res = await finalize2FA(token, twoFACode);
      if (res.verified) {
        notifications.success("2FA setup complete!");
        const next = { enabled: true, verified: true, secret_exists: true };
        setTwoFAStatus(next);
        persistTwoFAStatus(next);
        setQrCode(null);
        setTwoFACode("");
        setVerifyPanelOpen(false);
      }
    } catch (err) {
      notifications.error(err.detail || "Invalid code.");
    }
  };
  const openDisable2FAPanel = () => {
    clearModalState();
    setTwoFACode("");
    setShowDisablePanel(true);
  };

  const handleDisable2FA = async () => {
    const code = twoFACode.trim();
    if (!code || code.length < 6) {
      notifications.error("Enter the 6-digit code from your authenticator app.");
      return;
    }
    try {
      await disable2FA(token, code);
      notifications.success("2FA has been disabled.");
      setQrCode(null);
      setTwoFACode("");
      setShowDisablePanel(false);
      const reset = { enabled: false, verified: false, secret_exists: false };
      setTwoFAStatus(reset);
      persistTwoFAStatus(reset);
    } catch (err) {
      notifications.error(err.detail || "Failed to disable 2FA.");
    }
  };
  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleSyncWithSecureBucket = async () => {
    if (!token || !canAccessSecureArea) return;
    const targets =
      cloudProvider === "ALL" ? securityProviders : [cloudProvider];
    setIsSyncing(true);
    const loadingToastId = showLoading("Syncing secure vault with cloud storage…");
    try {
      let totalInserted = 0;
      let totalRemoved = 0;
      const skipped = [];

      for (const csp of targets) {
        try {
          const syncOpts = {
            bucket: selectedBucket || undefined,
            region: selectedRegion !== "all" ? selectedRegion : undefined,
          };
          if (csp === "Azure" && selectedBucket) {
            syncOpts.container = selectedBucket;
          }
          const result = await syncSecureVault(token, csp, syncOpts);
          totalInserted += result.inserted || 0;
          totalRemoved += result.removed || 0;
        } catch (err) {
          const msg = err.detail || err.message || "Secure vault sync failed.";
          if (
            cloudProvider === "ALL" &&
            csp !== "AWS" &&
            /not configured|credentials|missing/i.test(String(msg))
          ) {
            skipped.push(csp);
            continue;
          }
          throw err;
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
          `Secure sync complete (all providers). Added ${totalInserted} new file(s).${removedMsg}${skipMsg}`
        );
      } else {
        updateSuccess(
          loadingToastId,
          `Secure sync complete (${cloudProvider}). Added ${totalInserted} new file(s).${removedMsg}`
        );
      }
      await fetchSecureFiles();
    } catch (err) {
      updateError(
        loadingToastId,
        err.detail || err.message || "Secure vault sync failed."
      );
    } finally {
      setIsSyncing(false);
    }
  };

  const displayedSecureFiles = useMemo(() => {
    const withCsp = (secureFiles || []).map((f) => ({ ...f, csp: f.csp || "AWS" }));
    return filterFilesByCloudProvider(withCsp, cloudProvider);
  }, [secureFiles, cloudProvider]);

  const secureSyncActionLabel = useMemo(() => {
    if (selectedBucket) {
      return cloudProvider === "ALL"
        ? `Sync ${selectedBucket}`
        : `Sync ${selectedBucket} (${cloudProvider})`;
    }
    return cloudProvider === "ALL" ? "Sync secure vault (all)" : `Sync (${cloudProvider})`;
  }, [cloudProvider, selectedBucket]);

  const resetUploadState = () => {
    setPendingLocalFile(null);
    setPendingFileMeta(null);
    setShowSecureWizard(false);
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleStartSecureWizard = () => {
    if (!file) {
      notifications.info("Choose a file first, then open the upload wizard.");
      fileInputRef.current?.click();
      return;
    }
    if (!token) {
      notifications.error("Sign in to upload secure files.");
      return;
    }
    if (!securityProviders.length) {
      notifications.error(
        "No cloud is available for secure upload. Configure platform credentials in server .env or connect BYOC in Settings."
      );
      return;
    }
    setPendingLocalFile(file);
    setPendingFileMeta({ filename: file.name });
    setShowSecureWizard(true);
  };

  const handleWizardComplete = async ({
    encryptionMethod,
    password,
    csp,
    enableReplication,
    replicaRegion,
    isSensitive,
  }) => {
    if (!pendingLocalFile || !token) return;
    const filename = pendingLocalFile.name;
    setWizardSubmitting(true);
    const encryptLabel =
      encryptionMethod === "server-side" ? "cloud-managed" : "client-side";
    try {
      await executeWithNotification(
        async () => {
          if (encryptionMethod === "server-side") {
            await uploadSecureFile(pendingLocalFile, true, token, true, csp);
            await chooseEncryption(filename, "server-side", null, token, {
              csp,
              enableReplication,
              replicaRegion,
            });
          } else {
            const encryptedBlob = await encryptFileInBrowser(pendingLocalFile, password);
            await uploadClientEncrypted(encryptedBlob, filename, Boolean(isSensitive), token, {
              csp,
              enableReplication,
            });
          }
          resetUploadState();
          await fetchSecureFiles();
        },
        {
          loadingMessage: `Securing '${filename}' with ${encryptLabel} encryption…`,
          successMessage:
            encryptionMethod === "server-side"
              ? `'${filename}' stored with cloud-managed encryption on ${CSP_LABELS[csp] || csp}.`
              : `'${filename}' encrypted in your browser and stored on ${CSP_LABELS[csp] || csp}.`,
          getErrorMessage: (err) => {
            const msg = err.detail || err.message || "Secure upload failed";
            return typeof msg === "string" ? msg : "Secure upload failed";
          },
        }
      );
    } catch {
      /* toast already shown */
    } finally {
      setWizardSubmitting(false);
    }
  };

  const handleStartEncryptFlow = (fileRow) => {
    const meta = fileRow || {
      filename: pendingFileMeta?.filename,
      is_sensitive: pendingFileMeta?.is_sensitive,
      scan_reasons: pendingFileMeta?.scan_reasons,
    };
    setFileAwaitingEncryption(meta);
    setShowEncryptionModal(true);
  };

  const handleEncryptionChoice = async (encryptionMethod, password) => {
    if (!fileAwaitingEncryption) return;

    const encFilename = fileAwaitingEncryption.filename;
    try {
      await executeWithNotification(
        async () => {
          if (encryptionMethod === "server-side") {
            await chooseEncryption(encFilename, "server-side", null, token);
          } else if (encryptionMethod === "client-side") {
            if (!pendingLocalFile) {
              throw new Error(
                "Original file is no longer in memory. Please re-upload and choose client-side encryption immediately."
              );
            }
            const encryptedBlob = await encryptFileInBrowser(pendingLocalFile, password);
            await uploadClientEncrypted(
              encryptedBlob,
              encFilename,
              Boolean(fileAwaitingEncryption.is_sensitive ?? pendingFileMeta?.is_sensitive),
              token
            );
          }

          setShowEncryptionModal(false);
          setFileAwaitingEncryption(null);
          setPendingLocalFile(null);
          setPendingFileMeta(null);
          setShowSecureWizard(false);
          setFile(null);
          if (fileInputRef.current) fileInputRef.current.value = "";
          await fetchSecureFiles();
        },
        {
          loadingMessage: `Applying encryption to '${encFilename}'…`,
          successMessage:
            encryptionMethod === "server-side"
              ? `'${encFilename}' encrypted with SSE-S3 and stored (primary + replica).`
              : `'${encFilename}' encrypted in your browser and stored. Your password was not sent to the server.`,
          getErrorMessage: (err) => {
            const msg = err.detail || err.message || "Failed to apply encryption";
            return typeof msg === "string" ? msg : "Failed to apply encryption";
          },
        }
      );
    } catch (err) {
      throw err;
    }
  };

  const handleChooseEncryption = (file) => {
    handleStartEncryptFlow(file);
  };

  const handleDelete = async (fileRef) => {
    const filename = typeof fileRef === "string" ? fileRef : fileRef.filename;
    const bucket =
      typeof fileRef === "object"
        ? fileRef.cloud_bucket || selectedBucket
        : selectedBucket;
    setShowModal(false);
    setIsDeleting(filename);
    try {
      await executeWithNotification(
        async () => {
          await deleteSecureFile(filename, token, { bucket: bucket || undefined });
          await fetchSecureFiles();
        },
        {
          loadingMessage: `Deleting '${filename}' from secure vault…`,
          successMessage: `File '${filename}' was deleted successfully.`,
          getErrorMessage: (err) => err.detail || "Could not delete file.",
        }
      );
    } catch {
      /* toast already shown */
    } finally {
      setIsDeleting(null);
    }
  };

  const handleDownload = async (file) => {
    const loadingToastId = showLoading(`Preparing secure download for '${file.filename}'…`);
    try {
      const response = await getSecureDownloadUrl(file.filename, token, {
        bucket: file.cloud_bucket || selectedBucket || undefined,
      });

      if (response.client_side_encrypted) {
        setFileToDecrypt(file);
        setShowDecryptionModal(true);
        updateSuccess(
          loadingToastId,
          `'${file.filename}' is client-encrypted — enter your password to decrypt.`
        );
      } else {
        window.open(response.presigned_url, "_blank");
        updateSuccess(loadingToastId, `Download started for '${file.filename}'.`);
      }
    } catch (error) {
      updateError(loadingToastId, error.detail || "Could not get download link.");
    }
  };

  const handleDecryptDownload = async (password) => {
    if (!fileToDecrypt) return;

    const filename = fileToDecrypt.filename;
    const loadingToastId = showLoading(`Decrypting '${filename}' in your browser…`);
    try {
      const ciphertextBlob = await downloadClientCiphertext(filename, token, {
        bucket: fileToDecrypt.cloud_bucket || selectedBucket || undefined,
      });
      const plainBlob = await decryptBlobInBrowser(ciphertextBlob, password);
      downloadBlob(plainBlob, filename);
      updateSuccess(loadingToastId, "File decrypted in your browser and downloaded.");
      setShowDecryptionModal(false);
      setFileToDecrypt(null);
    } catch (error) {
      const detail = error.detail || error.message || "Decryption failed";
      updateError(loadingToastId, detail);
      throw new Error(detail);
    }
  };

  const renderEncryptionBadge = (f) => {
    if (f.awaiting_encryption_choice && f.encryption_status === "awaiting_choice") {
      return <span className="awaiting-tag">Action required</span>;
    }
    if (f.client_side_encrypted || f.encryption_method === "client-side") {
      return <span className="encrypted-tag cse-tag">CSE (browser)</span>;
    }
    if (f.encryption_method === "server-side" || (f.is_encrypted && !f.client_side_encrypted)) {
      return <span className="encrypted-tag sse-tag">SSE-S3</span>;
    }
    if (f.is_encrypted) {
      return <span className="encrypted-tag">Encrypted</span>;
    }
    return <span className="status-tag">Normal</span>;
  };

  const showSetupPanel = Boolean(
    qrCode && !twoFAStatus.enabled && twoFAStatus.secret_exists,
  );
  const showVerifyPanel = Boolean(
    twoFAStatus.enabled &&
      !twoFAStatus.verified &&
      twoFAStatus.secret_exists &&
      verifyPanelOpen,
  );
  const twoFAOverlayOpen = showSetupPanel || showVerifyPanel || showDisablePanel;

  useEffect(() => {
    if (!twoFAOverlayOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [twoFAOverlayOpen]);

  if (loading) {
    return <LoadingSpinner size="large" text="Loading security..." />;
  }

  const closeDisablePanel = () => {
    setShowDisablePanel(false);
    setTwoFACode("");
  };

  const codeInput = (placeholder, ariaLabel) => (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="one-time-code"
      placeholder={placeholder}
      value={twoFACode}
      onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, ""))}
      maxLength={6}
      className="twofa-input"
      aria-label={ariaLabel}
    />
  );

  return (
    <div className="security-page page-container zenith-page-enter">
        <TwoFADialog
          open={showSetupPanel}
          onClose={cancelTwoFASetup}
          titleId="twofa-dialog-title"
          title="Finalize 2FA setup"
          kicker="Secure vault"
          description="Scan this QR code with your authenticator app, then enter the 6-digit code below."
          primaryLabel="Finalize setup"
          onPrimary={handleFinalize2FA}
          cancelLabel="Cancel setup"
          onCancel={cancelTwoFASetup}
        >
          <div className="twofa-qr-wrap">
            <img src={qrCode} alt="2FA QR Code" className="twofa-qr" />
          </div>
          {codeInput("000000", "2FA verification code")}
        </TwoFADialog>

        <TwoFADialog
          open={showDisablePanel}
          onClose={closeDisablePanel}
          titleId="twofa-disable-title"
          title="Disable two-factor authentication"
          kicker="Account security"
          variant="danger"
          description="Enter the 6-digit code from your authenticator app to confirm you want to turn off 2FA."
          primaryLabel="Disable 2FA"
          primaryVariant="danger"
          onPrimary={handleDisable2FA}
          cancelLabel="Cancel"
          onCancel={closeDisablePanel}
        >
          {codeInput("000000", "2FA code to disable")}
        </TwoFADialog>

        <TwoFADialog
          open={showVerifyPanel}
          onClose={() => setVerifyPanelOpen(false)}
          titleId="twofa-verify-title"
          title="Verify your identity"
          kicker="Secure vault"
          description="Enter the 6-digit code from your authenticator app to unlock the secure vault."
          primaryLabel="Verify"
          primaryVariant="success"
          onPrimary={handleVerify2FA}
          cancelLabel="Not now"
          onCancel={() => setVerifyPanelOpen(false)}
        >
          {codeInput("000000", "2FA verification code")}
        </TwoFADialog>

        <div
          className={
            twoFAOverlayOpen ? "security-page__body security-page__body--dimmed" : "security-page__body"
          }
          aria-hidden={twoFAOverlayOpen ? true : undefined}
        >
        <PageHeader
          kicker="Secure vault"
          title="Security Center"
          subtitle="Scan, encrypt, and manage sensitive files with SSE-S3 or browser-side encryption."
          onRefresh={handlePageRefresh}
          refreshing={pageRefreshing}
          refreshDisabled={isSyncing || wizardSubmitting}
        />

        <div className="security-2fa-bar" role="region" aria-label="Two-factor authentication">
          <div className="security-2fa-bar__content">
            <span className="security-2fa-bar__icon" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </span>
            <div className="security-2fa-bar__text">
              <span className="security-2fa-bar__title">Two-factor authentication</span>
              <span className="security-2fa-bar__status">
                {twoFAStatus.enabled ? (
                  <>
                    <span className="security-2fa-badge security-2fa-badge--on">Enabled</span>
                    {twoFAStatus.verified
                      ? 'Your vault session is verified.'
                      : 'Verify your code to access the secure vault.'}
                  </>
                ) : (
                  <>
                    <span className="security-2fa-badge security-2fa-badge--off">Off</span>
                    Protect uploads with an authenticator app (recommended).
                  </>
                )}
              </span>
            </div>
          </div>
          <div className="security-2fa-bar__actions">
            {twoFAStatus.enabled ? (
              <>
                {!twoFAStatus.verified && !verifyPanelOpen && (
                  <button
                    type="button"
                    className="btn success-btn"
                    onClick={() => {
                      clearModalState();
                      setVerifyPanelOpen(true);
                    }}
                  >
                    Verify now
                  </button>
                )}
                <button type="button" className="btn danger-btn" onClick={openDisable2FAPanel}>
                  Disable 2FA
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleEnable2FA}
                className="btn success-btn"
                disabled={isEnabling2FA}
              >
                {isEnabling2FA ? 'Loading…' : 'Enable 2FA'}
              </button>
            )}
          </div>
        </div>

        <div className="page-card zenith-surface zenith-surface--accent-security">
          <h3 className="page-title">Secure File Upload</h3>
          <p className="page-description">
            Files are scanned for sensitive data. When sensitive content is found, you
            choose encryption (cloud-managed or browser), optional regional replication,
            and the target cloud (AWS, Google Cloud, or Azure).
          </p>
          {!availLoading && securityProviders.length === 0 && (
            <CloudAvailabilityBanner
              featureLabel="secure vault"
              credentialMode={credentialMode}
            />
          )}

          {/* Security Process Flow */}
          <div className="security-process-info">
            <div className="process-step">
              <div className="process-icon scan">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                  <line x1="12" y1="22.08" x2="12" y2="12"/>
                </svg>
              </div>
              <div className="process-text">
                <strong>Pattern-Based Scan</strong>
                <span>Regex detection across AWS, Azure, GCP, cards, credentials, and PII</span>
              </div>
            </div>

            <div className="process-step">
              <div className="process-icon encrypt">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              </div>
              <div className="process-text">
                <strong>AES-256 Encryption</strong>
                <span>Client or server-side options</span>
              </div>
            </div>

            <div className="process-step">
              <div className="process-icon replicate">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                  <polyline points="7.5 4.21 12 6.81 16.5 4.21"/>
                  <polyline points="7.5 19.79 7.5 14.6 3 12"/>
                  <polyline points="21 12 16.5 14.6 16.5 19.79"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                  <line x1="12" y1="22.08" x2="12" y2="12"/>
                </svg>
              </div>
              <div className="process-text">
                <strong>Data Replication</strong>
                <span>+20% cost for redundancy & backup</span>
              </div>
            </div>

            <div className="process-step">
              <div className="process-icon secure">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  <path d="M9 12l2 2 4-4"/>
                </svg>
              </div>
              <div className="process-text">
                <strong>Secure Storage</strong>
                <span>Multi-cloud vault with 2FA protection</span>
              </div>
            </div>
          </div>

          <div className="form-group horizontal-form security-upload-row">
            <input ref={fileInputRef} type="file" onChange={handleFileChange} className="file-input" />
            <button
              type="button"
              onClick={handleStartSecureWizard}
              disabled={wizardSubmitting || (!file && securityProviders.length === 0)}
              className="btn upload-btn"
            >
              {file ? "Configure & upload →" : "Select a file first"}
            </button>
          </div>
        </div>

        {canAccessSecureArea && (
          <div className="security-destination-panel">
            <BucketRegionSelector
              surface="security"
              storageKeyPrefix="zenith.security"
              selectedBucket={selectedBucket}
              selectedRegion={selectedRegion}
              onBucketChange={handleBucketSelect}
              onRegionChange={handleRegionSelect}
              reloadToken={catalogReloadToken}
            />
            <ByocStorageTargetBanner
              variant="security"
              selectedBucket={selectedBucket}
              selectedRegion={selectedRegion}
              activeCsp={cloudProvider}
            />
          </div>
        )}

        {/* Secure Files Table */}
        <div className="files-section zenith-surface zenith-surface--accent-security">
          <div className="list-header">
            <h3 className="section-title">Your Secure Files</h3>
            <CloudProviderToolbar
              className="security-cloud-toolbar"
              provider={cloudProvider}
              onProviderChange={setCloudProvider}
              onAction={handleSyncWithSecureBucket}
              actionLabel={secureSyncActionLabel}
              actionBusy={isSyncing}
              actionDisabled={!canAccessSecureArea}
              actionClassName="btn sync-btn"
              selectAriaLabel="Filter secure files by cloud provider"
              providerOptions={securityToolbarOptions}
            />
          </div>
          {!secureFiles || secureFiles.length === 0 ? (
            <EmptyState
              icon={<IconLock aria-hidden="true" />}
              title="No secure files yet"
              message="Upload a file to the vault. Sensitive content can be auto-protected with SSE-S3 or browser encryption."
            />
          ) : displayedSecureFiles.length === 0 ? (
            <EmptyState
              icon={<IconLock aria-hidden="true" />}
              title={`No ${cloudProvider} secure files`}
              message={
                cloudProvider === "ALL"
                  ? "No files match the current bucket filter."
                  : `No secure files on ${cloudProvider}. Try another cloud or sync the vault.`
              }
            />
          ) : (
          <div className="table-responsive-scroll">
          <table className="file-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size (KB)</th>
                <th>Upload Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedSecureFiles.map((f) => {
                  const showEncryptionChoice = f.awaiting_encryption_choice && f.encryption_status === 'awaiting_choice';
                  return (
                    <tr key={`${f.cloud_bucket || ""}-${f.s3_key || f.filename}`}>
                      <td>{f.filename}</td>
                      <td>{(f.size_bytes / 1024).toFixed(2)}</td>
                      <td className="date-col">
                        {f.upload_date ? new Date(f.upload_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td>{renderEncryptionBadge(f)}</td>
                      <td>
                        {isDeleting === f.filename ? (
                          <span className="deleting-indicator">Deleting...</span>
                        ) : showEncryptionChoice ? (
                          <button onClick={() => handleChooseEncryption(f)} className="action-btn primary-btn">
                            Encrypt this
                          </button>
                        ) : (
                          <>
                            <button onClick={() => handleDownload(f)} className="action-btn download-btn">
                              Download
                            </button>
                            <button onClick={() => { setFileToDelete(f); setShowModal(true); }} className="action-btn delete-btn">
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
          </div>
          )}
        </div>

        {showSecureWizard && pendingLocalFile && (
          <SecureUploadWizard
            file={pendingLocalFile}
            token={token}
            providers={securityProviders}
            selectedBucket={selectedBucket}
            selectedRegion={selectedRegion}
            onBucketChange={handleBucketSelect}
            onRegionChange={handleRegionSelect}
            isSubmitting={wizardSubmitting}
            onClose={() => {
              setShowSecureWizard(false);
              setPendingLocalFile(null);
            }}
            onComplete={handleWizardComplete}
          />
        )}

        {showEncryptionModal && fileAwaitingEncryption && (
          <EncryptionChoiceModal
            file={fileAwaitingEncryption}
            onClose={() => {
              setShowEncryptionModal(false);
              setFileAwaitingEncryption(null);
            }}
            onChoose={handleEncryptionChoice}
          />
        )}

        {showDecryptionModal && fileToDecrypt && (
          <DecryptionPasswordModal
            file={fileToDecrypt}
            onClose={() => {
              setShowDecryptionModal(false);
              setFileToDecrypt(null);
            }}
            onDecrypt={handleDecryptDownload}
          />
        )}

        {showModal && (
          <div className="confirm-modal-overlay">
            <div className="modal-content">
              <p>
                Are you sure you want to delete &apos;
                {typeof fileToDelete === "object" ? fileToDelete?.filename : fileToDelete}
                &apos;?
              </p>
              <div className="modal-buttons">
                <button
                  onClick={() => handleDelete(fileToDelete)}
                  className="btn danger-btn"
                >
                  Yes, Delete
                </button>
                <button onClick={() => setShowModal(false)} className="btn">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        </div>
    </div>
  );
}

export default SecurityPage;