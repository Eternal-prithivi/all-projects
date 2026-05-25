// =============================================================================
// PAGE: SecurityPage.jsx  (745 lines)
// ROUTE: /dashboard/security
// PURPOSE: 2FA management (enable/disable/verify) + secure file vault
//          (upload with auto sensitive-scan, two-step encryption choice, download, delete)
// API: Uses functions from ../api.js (status2FA, enable2FA, finalize2FA, verify2FA,
//      disable2FA, listSecureFiles, deleteSecureFile, uploadSecureFile, chooseEncryption,
//      decryptAndDownload) — NOT raw fetch() — imports from api.js named exports
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
  chooseEncryption,
  decryptAndDownload
} from "../api";

// --- MAIN COMPONENT ---

function SecurityPage() {
  const { token, user } = useAuth();
  const notifications = useNotifications();
  const [file, setFile] = useState(null);
  const [encrypt, setEncrypt] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
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

  const canAccessSecureArea = !twoFAStatus.enabled || twoFAStatus.verified;

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

  const handleUpload = async () => {
    if (!file || !token) return;
    setIsUploading(true);
    const uploadedFileName = file.name;
    try {
      const response = await uploadSecureFile(file, encrypt, token);
      
      // Check if encryption choice is needed IMMEDIATELY
      if (response.needs_encryption && response.status === 'awaiting_encryption_choice') {
        notifications.warning(`⚠️ Action Required: Choose encryption method for '${uploadedFileName}'`);
        await fetchSecureFiles(); // Refresh to show the file
      } else {
        notifications.success(`✅ '${uploadedFileName}' uploaded successfully!`);
        await fetchSecureFiles();
      }
    } catch (err) {
      notifications.error(err.detail || "Secure upload failed.");
    } finally {
      setIsUploading(false);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleChooseEncryption = (file) => {
    setFileAwaitingEncryption(file);
    setShowEncryptionModal(true);
  };

  const handleEncryptionChoice = async (encryptionMethod, password) => {
    if (!fileAwaitingEncryption) return;

    console.log('Sending encryption choice:', {
      filename: fileAwaitingEncryption.filename,
      encryptionMethod,
      hasPassword: !!password
    });

    try {
      await chooseEncryption(
        fileAwaitingEncryption.filename,
        encryptionMethod,
        password,
        token
      );
      notifications.success(`${encryptionMethod} encryption applied successfully for '${fileAwaitingEncryption.filename}'`);
      setShowEncryptionModal(false);
      setFileAwaitingEncryption(null);
      
      // Refresh file list immediately to show encrypted file
      await fetchSecureFiles();
    } catch (err) {
      console.error('Encryption choice error:', err);
      notifications.error(err.detail || "Failed to apply encryption");
    }
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

    console.log('=== DECRYPT HANDLER STARTED ===');
    console.log('File:', fileToDecrypt);
    console.log('Password length:', password?.length);
    console.log('Token exists:', !!token);

    try {
      console.log('Starting decryption for:', fileToDecrypt.filename);
      const response = await decryptAndDownload(fileToDecrypt.filename, password, token);
      console.log('Decryption response:', response);
      
      // Check your browser's Downloads folder!
      notifications.success("File decrypted and downloaded successfully! Check your Downloads folder.");
      setShowDecryptionModal(false);
      setFileToDecrypt(null);
    } catch (error) {
      console.error('=== DECRYPT ERROR CAUGHT ===');
      console.error('Error:', error);
      console.error('Error type:', typeof error);
      console.error('Error constructor:', error?.constructor?.name);
      console.error('Error message:', error?.message);
      console.error('Error detail:', error?.detail);
      console.error('Error stack:', error?.stack);
      throw new Error(error.detail || error.message || "Decryption failed");
    }
  };

  const pageStyles = `
    :root {
      --primary-gold: #d4af37; --hover-gold: #c8a430; --dark-bg: #121212;
      --content-bg: #1a1a1a; --border-color: #2a2a2a; --text-primary: #e0e0e0;
      --text-secondary: #a3a3a3; --danger-red: #dc3545; --primary-blue: #007bff;
      --success-green: #28a745;
    }
    .page-container { padding: 2rem; color: var(--text-primary); font-family: 'Inter', sans-serif; }
    .page-card { background: var(--content-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 2.5rem; margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    .page-title { font-size: 1.75rem; font-weight: 600; color: #fff; margin-top: 0; margin-bottom: 1.5rem; }
    .page-description { color: var(--text-secondary); margin-bottom: 2rem; line-height: 1.6; }
    .form-group { display: flex; flex-wrap: wrap; align-items: center; gap: 1.5rem; }
    .form-group.horizontal-form { flex-wrap: nowrap; justify-content: flex-start; align-items: center; gap: 1rem; }
    .form-group.horizontal-form .file-input { flex: 1; min-width: 0; }
    .form-group.horizontal-form .checkbox-group { flex-shrink: 0; white-space: nowrap; }
    .form-group.horizontal-form .upload-btn { flex-shrink: 0; white-space: nowrap; }
    .form-group input[type="file"] { color: #999; font-family: 'Inter', sans-serif; }
    .form-group input[type="file"]::file-selector-button { background-color: var(--primary-gold); color: #000; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; font-family: 'Inter', sans-serif; margin-right: 1rem; }
    .form-group input[type="file"]::file-selector-button:hover { background-color: var(--hover-gold); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(212, 175, 55, 0.2); }
    .checkbox-group { display: flex; align-items: center; gap: 0.5rem; }
    .checkbox-group label { margin: 0; cursor: pointer; user-select: none; }
    .btn { background-color: var(--primary-gold); color: #000; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; }
    .btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
    .btn.danger-btn { background-color: var(--danger-red); color: #fff; }
    .btn.danger-btn:hover { box-shadow: 0 6px 20px rgba(220, 53, 69, 0.3); }
    .btn.download-btn { background-color: var(--primary-blue); color: #fff; }
    .btn.download-btn:hover { box-shadow: 0 6px 20px rgba(0, 123, 255, 0.3); }
    .btn.success-btn { background-color: var(--success-green); color: #fff; }
    .btn.success-btn:hover { box-shadow: 0 6px 20px rgba(40, 167, 69, 0.3); }
    .btn:disabled { background-color: #444; color: #888; cursor: not-allowed; transform: none; box-shadow: none; }
    
    /* File table styles */
    .files-section { background: var(--content-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 2rem; margin-top: 2rem; }
    .section-title { font-size: 1.75rem; font-weight: 600; color: #fff; margin-top: 0; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 1rem; }
    .file-table { width: 100%; border-collapse: collapse; }
    .file-table thead th { background: #111; color: var(--text-secondary); font-weight: 600; text-align: left; padding: 1rem; border-bottom: 2px solid var(--border-color); text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.5px; }
    .file-table tbody td { padding: 1rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
    .file-table tbody tr:hover { background: #1c1c1c; }
    .file-table tbody tr:last-child td { border-bottom: none; }
    .date-col { color: var(--text-secondary); font-size: 0.9rem; }
    
    /* Status tags */
    .encrypted-tag { background-color: #6a0dad; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .awaiting-tag { background-color: #f59e0b; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .processing-tag { background-color: #10b981; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .status-tag { background-color: #4b5563; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    
    /* Action buttons */
    .action-btn { background-color: var(--primary-blue); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; margin-right: 0.5rem; transition: all 0.2s ease; font-size: 0.9rem; }
    .action-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    .action-btn.primary-btn { background-color: var(--primary-gold); color: #000; }
    .action-btn.download-btn { background-color: var(--primary-blue); }
    .action-btn.delete-btn { background-color: var(--danger-red); }
    .action-btn:last-child { margin-right: 0; }
    
    .deleting-indicator, .processing-indicator { color: var(--text-secondary); font-size: 0.9rem; font-style: italic; }
    .empty-list-message { color: var(--text-secondary); text-align: center; padding: 2rem; }
    .twofa-container { max-width: 500px; margin: 4rem auto; background: var(--content-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 2.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; }
    .twofa-title { font-size: 1.75rem; font-weight: 600; color: #fff; margin-top: 0; margin-bottom: 1rem; }
    .twofa-description { color: var(--text-secondary); margin-bottom: 2rem; line-height: 1.6; }
    .twofa-input { display: block; width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 1.5rem; border-radius: 8px; border: 1px solid var(--border-color); background: #111; color: var(--text-primary); font-size: 1.2rem; text-align: center; letter-spacing: 0.3em; }
    .confirm-modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; }
    .modal-content { background: #252525; padding: 2.5rem; border-radius: 12px; text-align: center; }
    .modal-content p { margin-bottom: 2rem; }
    .modal-buttons .btn { margin: 0 0.5rem; }
    
    /* Security Process Info */
    .security-process-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.5rem;
      margin: 2rem 0;
      padding: 1.5rem;
      background: #111;
      border-radius: 12px;
      border: 1px solid var(--border-color);
    }
    
    .process-step {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
    }
    
    .process-icon {
      width: 48px;
      height: 48px;
      min-width: 48px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .process-icon svg {
      width: 24px;
      height: 24px;
      z-index: 2;
    }
    
    .process-icon.scan {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
    
    .process-icon.encrypt {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      color: white;
    }
    
    .process-icon.replicate {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      color: white;
      animation: pulse 2s ease-in-out infinite;
    }
    
    .process-icon.secure {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
      color: white;
    }
    
    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
        box-shadow: 0 4px 12px rgba(0,242,254,0.3);
      }
      50% {
        transform: scale(1.05);
        box-shadow: 0 6px 20px rgba(0,242,254,0.5);
      }
    }
    
    .process-text {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    
    .process-text strong {
      color: #fff;
      font-size: 0.95rem;
      font-weight: 600;
    }
    
    .process-text span {
      color: var(--text-secondary);
      font-size: 0.85rem;
      line-height: 1.4;
    }
    
    @media (max-width: 768px) {
      .security-process-info {
        grid-template-columns: 1fr;
        gap: 1rem;
      }
      
      .process-step {
        padding: 0.5rem;
      }
      
      .form-group.horizontal-form {
        flex-wrap: wrap;
      }
    }
  `;

  if (loading)
    return (
      <div className="page-container">
        <p>Loading...</p>
      </div>
    );

  // --- NEW ORDER OF CONDITIONAL RENDERING ---

  // 1. Show QR code setup if qrCode is present and 2FA is not yet enabled
  if (qrCode && !twoFAStatus.enabled && twoFAStatus.secret_exists) {
    return (
      <>
        <style>{pageStyles}</style>
        <div className="twofa-container">
          <h3 className="twofa-title">Finalize 2FA Setup</h3>
          <p className="twofa-description">
            Scan this QR code, then enter the code from your app below.
          </p>
          <img
            src={qrCode}
            alt="2FA QR Code"
            style={{
              display: "block",
              width: "250px", // Increased size for visibility
              height: "250px", // Increased size for visibility
              margin: "0 auto 2rem auto",
              background: "white",
              borderRadius: "8px",
              border: '5px solid red', // Added red border for debugging
            }}
          />
          <input
            type="text"
            placeholder="Enter code to finalize"
            value={twoFACode}
            onChange={(e) => setTwoFACode(e.target.value)}
            maxLength="6"
            className="twofa-input"
          />
          <button
            onClick={handleFinalize2FA}
            className="btn"
            style={{ width: "100%" }}
          >
            Finalize Setup
          </button>
        </div>
      </>
    );
  }

  // 2. Show 2FA verification if 2FA is enabled but not yet verified to access secure content
  if (twoFAStatus.enabled && !twoFAStatus.verified && twoFAStatus.secret_exists) {
    return (
      <>
        <style>{pageStyles}</style>
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
          />
          <button
            onClick={handleVerify2FA}
            className="btn"
            style={{ width: "100%" }}
          >
            Verify
          </button>
        </div>
      </>
    );
  }


  // 3. Default return: main security page content (file upload, enable/disable button, file list)
  return (
    <>
      <style>{pageStyles}</style>
      <div className="page-container">
        <div className="page-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h3 className="page-title" style={{ marginBottom: 0 }}>Secure File Upload</h3>
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
            Files uploaded here are automatically scanned for sensitive data. If
            found, they will be encrypted.
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
              <label htmlFor="encrypt-manual">Encrypt manually</label>
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
          <h3 className="section-title">Your Secure Files</h3>
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
                      <td>
                        {f.is_encrypted && <span className="encrypted-tag">Encrypted</span>}
                        {showEncryptionChoice && <span className="awaiting-tag">⚠️ Action Required</span>}
                        {!f.is_encrypted && !showEncryptionChoice && <span className="status-tag">Normal</span>}
                      </td>
                      <td>
                        {isDeleting === f.filename ? (
                          <span className="deleting-indicator">Deleting...</span>
                        ) : showEncryptionChoice ? (
                          <button onClick={() => handleChooseEncryption(f)} className="action-btn primary-btn">
                            Choose Encryption
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
    </>
  );
}

export default SecurityPage;