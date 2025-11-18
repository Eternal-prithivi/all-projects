import React, { useState, useEffect, useCallback, useRef } from "react";
import { toast, ToastContainer } from "react-toastify";
import "../styles/storage.css"; // We use the external stylesheet

// --- MOCKED DEPENDENCIES for a self-contained component ---
const useAuth = () => ({
  token: localStorage.getItem("authToken"),
  user: { username: "tanjiro" },
});

// --- API FUNCTIONS ---
const API_BASE_URL = "http://localhost:8000/api";
const handleApiResponse = async (response) => {
  if (!response.ok) {
    // --- MODIFIED: Ensure error details from FastAPI are caught ---
    const errorBody = await response.json();
    throw new Error(errorBody.detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return { success: true };
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json") ? response.json() : {};
};
const listFiles = (token) =>
  fetch(`${API_BASE_URL}/storage/files`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);
const getDownloadUrl = (filename, token) =>
  fetch(`${API_BASE_URL}/storage/download/${filename}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);
const deleteFile = (filename, token) =>
  fetch(`${API_BASE_URL}/storage/delete/${filename}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleApiResponse);
const analyzeFile = (data, token) =>
  fetch(`${API_BASE_URL}/storage/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  }).then(handleApiResponse);
const uploadFileToCSP = (file, csp, storageClass, token) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("csp", csp);
  formData.append("storage_class", storageClass);
  return fetch(`${API_BASE_URL}/storage/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  }).then(handleApiResponse);
};

// --- NEW API FUNCTION: To initiate Glacier restore ---
const initiateGlacierRestore = (filename, tier, days, token) => {
  const formData = new FormData(); // FastAPI expects form-urlencoded for Form parameters
  formData.append("tier", tier);
  formData.append("days", days);
  return fetch(`${API_BASE_URL}/storage/restore-aws/${filename}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData, // FormData automatically sets 'Content-Type: multipart/form-data'
  }).then(handleApiResponse);
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

// --- MAIN STORAGE PAGE COMPONENT ---

function StoragePage() {
  const { token } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
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
      toast.error(error.message || "Failed to fetch files."); // --- MODIFIED: Use error.message ---
    } finally {
      setIsLoading(false);
    }
  }, [token]);

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
      toast.error(error.message || "Analysis failed."); // --- MODIFIED: Use error.message ---
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
      toast.success(
        `'${selectedFile.name}' uploaded successfully to ${finalCsp}!`
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchFiles();
    } catch (error) {
      toast.error(error.message || `Upload to ${finalCsp} failed.`); // --- MODIFIED: Use error.message ---
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
      toast.success(`'${fileToDelete}' deleted successfully.`);
      await fetchFiles();
    } catch (error) {
      toast.error(error.message || "Failed to delete file."); // --- MODIFIED: Use error.message ---
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
        toast.info("This file is in Glacier. It needs to be restored before download.");
      } else if (error.message.includes("is currently being restored") && error.message.includes("409")) {
        toast.info(error.message); // Inform user it's already restoring
      }
      else {
        toast.error(error.message || "Could not get download link.");
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
      toast.success(result.message || `'${fileToRestore}' restore initiated.`);
      setShowRestoreModal(false);
      setFileToRestore(null);
      // Re-fetch files to potentially update their status in the UI
      await fetchFiles();
    } catch (error) {
      toast.error(error.message || `Failed to initiate restore for '${fileToRestore}'.`);
    } finally {
      setIsRestoring(false);
    }
  };

  const finalUploadDestination =
    manualCspSelection || (recommendation && recommendation.recommendation.csp);

  return (
    <div className="storage-container">
      <ToastContainer theme="dark" position="top-right" autoClose={5000} />
      <div className="storage-header">
        <h2>Standard Storage</h2>
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
              className={`priority-select priority-${userPriority}`}
            >
              <option value="balanced">Balanced</option>
              <option value="cost">Prioritize Cost Savings</option>
              <option value="performance">Prioritize Performance</option>
            </select>

            <label>Intended Use:</label>
            <select
              value={userIntent}
              onChange={(e) => setUserIntent(e.target.value)}
              className={`intent-select intent-${userIntent}`}
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
        <h3 className="list-title">Your Files</h3>
        {isLoading ? (
          <p>Loading files...</p>
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
              <button onClick={confirmDelete} className="modal-btn confirm">
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

            <div className="override-section">
              <label>Or, manually select a different provider:</label>
              <select
                className="override-select"
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
                className="restore-select"
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