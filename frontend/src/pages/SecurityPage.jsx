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
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNotifications } from "../hooks/useNotifications";
import EncryptionChoiceModal from "../components/EncryptionChoiceModal";
import DecryptionPasswordModal from "../components/DecryptionPasswordModal";
import EncryptSensitivePromptModal from "../components/EncryptSensitivePromptModal";
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
  syncAwsSecureBucket,
  chooseEncryption,
  uploadClientEncrypted,
  downloadClientCiphertext,
} from "../api";
import "../styles/security-page.css";

// --- MAIN COMPONENT ---

function SecurityPage() {
  const { token, user } = useAuth();
  const notifications = useNotifications();
  const [file, setFile] = useState(null);
  const [encrypt, setEncrypt] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
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
  const fileInputRef = useRef(null);
  const [showModal, setShowModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(null);
  const pollIntervalRef = useRef(null);
  const [showEncryptionModal, setShowEncryptionModal] = useState(false);
  const [fileAwaitingEncryption, setFileAwaitingEncryption] = useState(null);
  const [showDecryptionModal, setShowDecryptionModal] = useState(false);
  const [fileToDecrypt, setFileToDecrypt] = useState(null);
  const [showEncryptPrompt, setShowEncryptPrompt] = useState(false);
  const [pendingLocalFile, setPendingLocalFile] = useState(null);
  const [pendingFileMeta, setPendingFileMeta] = useState(null);
  const [alwaysAskEncryption, setAlwaysAskEncryption] = useState(() => {
    try {
      return localStorage.getItem("zenith-always-ask-encryption") === "true";
    } catch {
      return false;
    }
  });

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
      const files = await listSecureFiles(token);
      setSecureFiles(files);
      sessionStorage.setItem('cache_secureFiles', JSON.stringify(files));
      return files;
    } catch (err) {
      notifications.error("Could not fetch secure file list.");
      return [];
    }
  }, [token, canAccessSecureArea]);

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
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [user, token, canAccessSecureArea, fetchSecureFiles, loading]);

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
      } catch (err) {
        if (err.detail?.includes("2FA token verification is required")) {
          const status = { enabled: true, verified: false, secret_exists: true };
          setTwoFAStatus(status);
          sessionStorage.setItem('cache_2faStatus', JSON.stringify(status));
        }
      } finally {
        setLoading(false);
      }
    };
    check2FA();
  }, [token]);

  const handleVerify2FA = async () => {
    try {
      const res = await verify2FA(token, twoFACode);
      if (res.verified) {
        notifications.success("2FA verified successfully!");
        setTwoFAStatus((prev) => ({ ...prev, verified: true }));
      }
    } catch (err) {
      notifications.error(err.detail || "Error verifying 2FA");
    }
  };
  const handleEnable2FA = async () => {
    try {
      const res = await enable2FA(token);
      if (res.qr_code) {
        setQrCode(res.qr_code);
        console.log("State set: qrCode =", res.qr_code ? "SET" : "NOT SET");
        setTwoFAStatus((prev) => ({
          ...prev,
          secret_exists: true,
          enabled: false, // 2FA is not fully enabled until finalized
        }));
      }
    } catch (err) {
      notifications.error(err.detail || "Failed to enable 2FA");
    }
  };
  const handleFinalize2FA = async () => {
    try {
      const res = await finalize2FA(token, twoFACode);
      if (res.verified) {
        notifications.success("2FA setup complete!");
        setTwoFAStatus({ enabled: true, verified: true, secret_exists: true });
        setQrCode(null); // Clear QR code after successful setup
      }
    } catch (err) {
      notifications.error(err.detail || "Invalid code.");
    }
  };
  const handleDisable2FA = async () => {
    try {
      await disable2FA(token);
      notifications.success("2FA has been disabled.");
      setTwoFAStatus({ enabled: false, verified: false, secret_exists: false });
    } catch (err) {
      notifications.error(err.detail || "Failed to disable 2FA.");
    }
  };
  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleSyncWithSecureBucket = async () => {
    if (!token || !canAccessSecureArea) return;
    setIsSyncing(true);
    try {
      const result = await syncAwsSecureBucket(token);
      const scanned = result.scanned_prefix
        ? `prefix '${result.scanned_prefix}'`
        : "the secure vault";
      const removedMsg = result.removed > 0 ? ` Removed ${result.removed} stale record(s).` : "";
      notifications.success(
        `Secure sync complete. Added ${result.inserted} new file(s) from AWS after scanning ${scanned}.${removedMsg}`
      );
      await fetchSecureFiles();
    } catch (err) {
      notifications.error(err.detail || err.message || "Secure vault sync failed.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleUpload = async () => {
    if (!file || !token) return;
    setIsUploading(true);
    const uploadedFileName = file.name;
    try {
      const response = await uploadSecureFile(file, encrypt, token, alwaysAskEncryption);

      if (response.status === "auto_encrypted_sse") {
        notifications.success(
          response.message ||
            `'${uploadedFileName}' was auto-protected with SSE-S3 (sensitive data detected).`
        );
        setPendingLocalFile(null);
        setPendingFileMeta(null);
        setShowEncryptPrompt(false);
        await fetchSecureFiles();
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else if (response.needs_encryption && response.status === "awaiting_encryption_choice") {
        setPendingLocalFile(file);
        setPendingFileMeta({
          filename: uploadedFileName,
          is_sensitive: response.is_sensitive,
          scan_reasons: response.scan_reasons || [],
        });
        setShowEncryptPrompt(true);
        notifications.warning(
          `Sensitive data detected in '${uploadedFileName}'. Please encrypt this file.`
        );
        await fetchSecureFiles();
      } else {
        notifications.success(`'${uploadedFileName}' uploaded to your secure vault.`);
        setPendingLocalFile(null);
        setPendingFileMeta(null);
        setShowEncryptPrompt(false);
        await fetchSecureFiles();
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (err) {
      notifications.error(err.detail || "Secure upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleStartEncryptFlow = (fileRow) => {
    const meta = fileRow || {
      filename: pendingFileMeta?.filename,
      is_sensitive: pendingFileMeta?.is_sensitive,
      scan_reasons: pendingFileMeta?.scan_reasons,
    };
    setFileAwaitingEncryption(meta);
    setShowEncryptPrompt(false);
    setShowEncryptionModal(true);
  };

  const handleEncryptionChoice = async (encryptionMethod, password) => {
    if (!fileAwaitingEncryption) return;

    try {
      if (encryptionMethod === "server-side") {
        await chooseEncryption(
          fileAwaitingEncryption.filename,
          "server-side",
          null,
          token
        );
        notifications.success(
          `'${fileAwaitingEncryption.filename}' encrypted with SSE-S3 and stored (primary + replica).`
        );
      } else if (encryptionMethod === "client-side") {
        if (!pendingLocalFile) {
          throw new Error(
            "Original file is no longer in memory. Please re-upload and choose client-side encryption immediately."
          );
        }
        const encryptedBlob = await encryptFileInBrowser(pendingLocalFile, password);
        await uploadClientEncrypted(
          encryptedBlob,
          fileAwaitingEncryption.filename,
          Boolean(fileAwaitingEncryption.is_sensitive ?? pendingFileMeta?.is_sensitive),
          token
        );
        notifications.success(
          `'${fileAwaitingEncryption.filename}' encrypted in your browser and stored. Your password was not sent to the server.`
        );
      }

      setShowEncryptionModal(false);
      setFileAwaitingEncryption(null);
      setPendingLocalFile(null);
      setPendingFileMeta(null);
      setShowEncryptPrompt(false);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchSecureFiles();
    } catch (err) {
      const msg = err.detail || err.message || "Failed to apply encryption";
      notifications.error(typeof msg === "string" ? msg : "Failed to apply encryption");
      throw err;
    }
  };

  const handleChooseEncryption = (file) => {
    handleStartEncryptFlow(file);
  };

  const handleDelete = async (filename) => {
    setShowModal(false);
    setIsDeleting(filename);
    try {
      await deleteSecureFile(filename, token);
      await fetchSecureFiles();
      notifications.success(`File '${filename}' was deleted successfully.`);
    } catch (err) {
      notifications.error(err.detail || "Could not delete file.");
    } finally {
      setIsDeleting(null);
    }
  };

  const handleDownload = async (file) => {
    try {
      const response = await getSecureDownloadUrl(file.filename, token);
      
      // Check if file is client-side encrypted
      if (response.client_side_encrypted) {
        // Show password modal
        setFileToDecrypt(file);
        setShowDecryptionModal(true);
      } else {
        // Direct download for non-encrypted or server-side encrypted files
        window.open(response.presigned_url, "_blank");
      }
    } catch (error) {
      notifications.error(error.detail || "Could not get download link.");
    }
  };

  const handleDecryptDownload = async (password) => {
    if (!fileToDecrypt) return;

    try {
      const ciphertextBlob = await downloadClientCiphertext(
        fileToDecrypt.filename,
        token
      );
      const plainBlob = await decryptBlobInBrowser(ciphertextBlob, password);
      downloadBlob(plainBlob, fileToDecrypt.filename);
      notifications.success("File decrypted in your browser and downloaded.");
      setShowDecryptionModal(false);
      setFileToDecrypt(null);
    } catch (error) {
      const detail = error.detail || error.message;
      throw new Error(detail || "Decryption failed");
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

  if (loading)
    return (
      <div className="security-page page-container">
        <p>Loading...</p>
      </div>
    );

  // --- NEW ORDER OF CONDITIONAL RENDERING ---

  // 1. Show QR code setup if qrCode is present and 2FA is not yet enabled
  if (qrCode && !twoFAStatus.enabled && twoFAStatus.secret_exists) {
    return (
      <div className="security-page">
        <div className="twofa-container">
          <h3 className="twofa-title">Finalize 2FA Setup</h3>
          <p className="twofa-description">
            Scan this QR code, then enter the code from your app below.
          </p>
          <img src={qrCode} alt="2FA QR Code" className="twofa-qr" />
          <input
            type="text"
            placeholder="Enter code to finalize"
            value={twoFACode}
            onChange={(e) => setTwoFACode(e.target.value)}
            maxLength="6"
            className="twofa-input"
            aria-label="2FA verification code"
          />
          <button type="button" onClick={handleFinalize2FA} className="btn btn--block">
            Finalize Setup
          </button>
        </div>
      </div>
    );
  }

  // 2. Show 2FA verification if 2FA is enabled but not yet verified to access secure content
  if (twoFAStatus.enabled && !twoFAStatus.verified && twoFAStatus.secret_exists) {
    return (
      <div className="security-page">
        <div className="twofa-container">
          <h3 className="twofa-title">Two-Factor Authentication</h3>
          <p className="twofa-description">
            Enter the 6-digit code from your authenticator app to continue.
          </p>
          <input
            type="text"
            placeholder="6-digit code"
            value={twoFACode}
            onChange={(e) => setTwoFACode(e.target.value)}
            maxLength="6"
            className="twofa-input"
            aria-label="2FA verification code"
          />
          <button type="button" onClick={handleVerify2FA} className="btn btn--block">
            Verify
          </button>
        </div>
      </div>
    );
  }


  // 3. Default return: main security page content (file upload, enable/disable button, file list)
  return (
    <div className="security-page page-container">
        <div className="page-card">
          <div className="page-header-row">
            <div>
              <h3 className="page-title page-title--inline">Secure File Upload</h3>
            </div>
            <div>
              {twoFAStatus.enabled ? (
                <button className="btn danger-btn" onClick={handleDisable2FA}>
                  Disable 2FA
                </button>
              ) : (
                <button onClick={handleEnable2FA} className="btn success-btn">
                  Enable 2FA
                </button>
              )}
            </div>
          </div>
          <p className="page-description">
            Files are scanned for sensitive data. By default, sensitive files are
            auto-protected with SSE-S3. Enable the option below to always choose
            server-side vs browser encryption.
          </p>

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
                <strong>AI-Powered Scan</strong>
                <span>Automatic detection of sensitive data</span>
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
                <span>AWS S3 with 2FA protection</span>
              </div>
            </div>
          </div>

          <div className="form-group horizontal-form">
            <input ref={fileInputRef} type="file" onChange={handleFileChange} className="file-input" />
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="encrypt-manual"
                checked={encrypt}
                onChange={() => setEncrypt(!encrypt)}
              />
              <label htmlFor="encrypt-manual">Choose encryption method (SSE or browser)</label>
            </div>
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="always-ask-encryption"
                checked={alwaysAskEncryption}
                onChange={(e) => handleAlwaysAskChange(e.target.checked)}
              />
              <label htmlFor="always-ask-encryption">Always ask before encrypting sensitive files</label>
            </div>
            <button
              onClick={handleUpload}
              disabled={isUploading || !file}
              className="btn upload-btn"
            >
              {isUploading ? "Uploading..." : "Upload Secure File"}
            </button>
          </div>
        </div>
        {/* Secure Files Table */}
        <div className="files-section">
          <div className="list-header">
            <h3 className="section-title">Your Secure Files</h3>
            <button
              type="button"
              className="btn sync-btn"
              onClick={handleSyncWithSecureBucket}
              disabled={isSyncing}
            >
              {isSyncing ? "Syncing..." : "Sync with Bucket (AWS)"}
            </button>
          </div>
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
              {secureFiles && secureFiles.length > 0 ? (
                secureFiles.map((f) => {
                  const showEncryptionChoice = f.awaiting_encryption_choice && f.encryption_status === 'awaiting_choice';
                  return (
                    <tr key={f.filename}>
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
                            <button onClick={() => { setFileToDelete(f.filename); setShowModal(true); }} className="action-btn delete-btn">
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center" }}>
                    No secure files have been uploaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {showEncryptPrompt && pendingFileMeta && (
          <EncryptSensitivePromptModal
            file={{ filename: pendingFileMeta.filename }}
            scanReasons={pendingFileMeta.scan_reasons}
            onEncrypt={() => handleStartEncryptFlow(pendingFileMeta)}
            onDismiss={() => setShowEncryptPrompt(false)}
          />
        )}

        {/* Encryption Choice Modal */}
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

        {/* Decryption Password Modal */}
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
              <p>Are you sure you want to delete '{fileToDelete}'?</p>
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
  );
}

export default SecurityPage;