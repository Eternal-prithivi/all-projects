// =============================================================================
// PAGE: StoragePage.jsx  (564 lines)
// ROUTE: /dashboard/storage
// PURPOSE: Standard (non-secure) multi-cloud file management — ML-guided placement
//          (analyze → recommendation modal → confirm), upload to AWS/GCP/Azure,
//          list files, download (access tracked), delete, Glacier restore, AWS sync
// API: Uses api.js (listFiles, getDownloadUrl, deleteFile, uploadFile, syncAwsBucket)
//      + local apiClient wrappers for analyzeFile and initiateGlacierRestore
// STATE: files, recommendation, modals for delete/restore/recommendation
// BACKEND: /api/storage/* — analyze, upload, files, download, delete, sync/aws, restore-aws
// DO NOT:
//   - Skip the analyze → recommendation modal → confirm flow (ML prediction must be logged)
//   - Hardcode CSP — always read from file.csp or recommendation.recommendation.csp
//   - Remove access tracking in download (feeds access_frequency_score for ML tiering)
// =============================================================================
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNotifications } from "../hooks/useNotifications";
import { TableSkeleton } from "../components/Skeletons.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import {
  listFiles,
  getDownloadUrl,
  deleteFile,
  uploadFile as uploadFileToCSP,
  syncAwsBucket,
} from "../api";
import "../styles/storage.css";
import PageHeader from "../components/ui/PageHeader.jsx";

// --- API FUNCTIONS (Missing from api.js) ---
import { apiClient } from "../api";
const analyzeFile = async (data, token) => {
  const response = await apiClient.post("/storage/analyze", data);
  return response.data;
};
const initiateGlacierRestore = async (filename, tier, days, token) => {
  const formData = new FormData();
  formData.append("tier", tier);
  formData.append("days", days);
  const response = await apiClient.post(`/storage/restore-aws/${encodeURIComponent(filename)}`, formData);
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
  } = useNotifications();
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);

  const [userPriority, setUserPriority] = useState("balanced");
  const [userIntent, setUserIntent] = useState("active");
  const [showRecommendationModal, setShowRecommendationModal] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [manualCspSelection, setManualCspSelection] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

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
      const fileList = await listFiles(token);
      setFiles(fileList);
    } catch (error) {
      notifyError(error.message || "Failed to fetch files.");
    } finally {
      setIsLoading(false);
    }
  }, [token, notifyError]);

  const handleSyncWithBucket = async () => {
    if (!token) return;
    setIsSyncing(true);
    try {
      const result = await syncAwsBucket(token);
      const scanned = result.scanned_prefix ? `prefix '${result.scanned_prefix}'` : "the whole bucket";
      const removedMsg = result.removed > 0 ? ` Removed ${result.removed} stale record(s).` : "";
      notifySuccess(`Sync complete. Added ${result.inserted} new file(s) from AWS after scanning ${scanned}.${removedMsg}`);
      await fetchFiles();
    } catch (error) {
      notifyError(error.detail || error.message || "Sync failed.");
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleAnalyzeAndUpload = async () => {
    if (!selectedFile) return;
    setManualCspSelection(null);
    setIsAnalyzing(true);
    try {
      const analysisRequest = {
        filename: selectedFile.name,
        file_size_mb: selectedFile.size / (1024 * 1024),
        user_priority: userPriority,
        user_intent: userIntent,
      };
      const result = await analyzeFile(analysisRequest, token);
      setRecommendation(result);
      setShowRecommendationModal(true);
    } catch (error) {
      notifyError(error.message || "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const confirmAndUpload = async () => {
    if (!selectedFile || !token || !recommendation) return;

    // Determine the final CSP choice
    const finalCsp = manualCspSelection || recommendation.recommendation.csp;

    // --- CRITICAL FIX: Look up the correct storage class name for the chosen CSP ---
    // It uses the new 'options_by_csp' dictionary from the backend.
    const storageClass = recommendation.options_by_csp[finalCsp].service_name;

    setShowRecommendationModal(false);
    setIsUploading(true);

    try {
      await uploadFileToCSP(selectedFile, finalCsp, storageClass, token);
      notifySuccess(
        `'${selectedFile.name}' uploaded successfully to ${finalCsp}!`
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchFiles();
    } catch (error) {
      notifyError(error.message || `Upload to ${finalCsp} failed.`);
    } finally {
      setIsUploading(false);
    }
  };

  const openDeleteConfirmation = (filename) => {
    setFileToDelete(filename);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!fileToDelete) return;
    try {
      await deleteFile(fileToDelete, token);
      notifySuccess(`'${fileToDelete}' deleted successfully.`);
      await fetchFiles();
    } catch (error) {
      notifyError(error.message || "Failed to delete file.");
    } finally {
      setShowDeleteModal(false);
      setFileToDelete(null);
    }
  };

  // --- MODIFIED handleDownload to manage Glacier restores ---
  const handleDownload = async (filename) => {
    try {
      const { presigned_url } = await getDownloadUrl(filename, token);
      window.open(presigned_url, "_blank");
    } catch (error) {
      // Check for the specific Glacier error message and status code from backend
      if (error.message.includes("is in GLACIER storage") && error.message.includes("412")) {
        setFileToRestore(filename);
        setShowRestoreModal(true); // Open the restore modal
        notifyInfo("This file is in Glacier. It needs to be restored before download.");
      } else if (error.message.includes("is currently being restored") && error.message.includes("409")) {
        notifyInfo(error.message); // Inform user it's already restoring
      }
      else {
        notifyError(error.message || "Could not get download link.");
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
      const result = await initiateGlacierRestore(fileToRestore, restoreTier, restoreDays, token);
      notifySuccess(result.message || `'${fileToRestore}' restore initiated.`);
      setShowRestoreModal(false);
      setFileToRestore(null);
      // Re-fetch files to potentially update their status in the UI
      await fetchFiles();
    } catch (error) {
      notifyError(error.message || `Failed to initiate restore for '${fileToRestore}'.`);
    } finally {
      setIsRestoring(false);
    }
  };

  const finalUploadDestination =
    manualCspSelection || (recommendation && recommendation.recommendation.csp);

  return (
    <div className="storage-container">
      <PageHeader
        kicker="Object storage"
        title="Standard Storage"
        subtitle="Upload, analyze, and sync files across your connected cloud providers"
      />

      {/* Storage Process Flow */}
      <div className="storage-process-info">
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

      <div className="upload-section">
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

      <div className="list-section">
        <div className="list-header">
          <h3 className="list-title">Your Files</h3>
          <button
            type="button"
            className="action-btn"
            onClick={handleSyncWithBucket}
            disabled={isSyncing}
          >
            {isSyncing ? "Syncing..." : "Sync with Bucket (AWS)"}
          </button>
        </div>
        {isLoading ? (
          <TableSkeleton rows={5} columns={5} />
        ) : (
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
              {files.length > 0 ? (
                files.map((file) => (
                  <tr key={file.filename}>
                    <td>{file.filename}</td>
                    <td>{(file.size_bytes / 1024).toFixed(2)}</td>
                    <td className="date-col">
                      {new Date(file.upload_date).toLocaleString()}
                    </td>
                    <td>
                      <div className="csp-location-cell">
                        <CspIcon csp={file.csp} />
                        <span>{file.storage_class}</span>
                      </div>
                    </td>
                    <td>
                      <button
                        onClick={() => handleDownload(file.filename)}
                        className="action-btn download-btn"
                      >
                        Download
                      </button>
                      {/* --- NEW: Restore button for AWS Glacier/Deep Archive files --- */}
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
                        onClick={() => openDeleteConfirmation(file.filename)}
                        className="action-btn delete-btn"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center" }}>
                    No files uploaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <p>Are you sure you want to delete '{fileToDelete}'?</p>
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

      {showRecommendationModal && recommendation && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h4 className="recommendation-title">Analysis Complete</h4>
            <p className="recommendation-text">
              We've analyzed <strong>{selectedFile.name}</strong>. Based on its
              profile and your preferences, we've classified it as{" "}
              <strong>{recommendation.determined_tier} storage</strong>.
            </p>
            <div className="recommendation-box">
              <p>The most cost-effective option is:</p>
              <p className="recommendation-csp">
                <CspIcon csp={recommendation.recommendation.csp} />
                {recommendation.recommendation.csp} -{" "}
                {recommendation.recommendation.service_name}
              </p>
            </div>

            {recommendation.expert_votes?.length > 0 && (
              <div className="ensemble-box">
                <div className="ensemble-summary">
                  <span>Ensemble confidence</span>
                  <strong>{formatPercent(recommendation.ensemble_confidence)}</strong>
                </div>
                <div className="expert-votes">
                  {recommendation.expert_votes.map((vote) => (
                    <div className="expert-vote" key={vote.expert}>
                      <span>{formatExpertName(vote.expert)}</span>
                      <strong>{vote.predicted_tier}</strong>
                      <small>{formatPercent(vote.confidence)}</small>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="override-section">
              <label>Or, manually select a different provider:</label>
              <select
                className="zenith-select override-select"
                onChange={(e) => setManualCspSelection(e.target.value)}
                defaultValue={""}
              >
                <option value="">Use Recommended</option>
                <option value="AWS">Amazon Web Services</option>
                <option value="GCP">Google Cloud Platform</option>
                <option value="Azure">Microsoft Azure</option>
              </select>
            </div>

            <div className="modal-buttons">
              <button
                className="modal-btn cancel"
                onClick={() => setShowRecommendationModal(false)}
              >
                Cancel
              </button>
              <button
                className="modal-btn confirm"
                onClick={confirmAndUpload}
                disabled={isUploading}
              >
                {isUploading
                  ? "Uploading..."
                  : `Confirm & Upload to ${finalUploadDestination}`}
              </button>
            </div>
          </div>
        </div>
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
