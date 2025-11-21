import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNotifications } from "../hooks/useNotifications";

// --- SELF-CONTAINED DEPENDENCIES ---

const mockUser = { username: "tanjiro" };
const useAuth = () => ({
  token: localStorage.getItem("authToken"),
  user: mockUser,
});

// --- FIX: Added a new InfoTooltip component ---
const InfoTooltip = ({ text }) => (
  <div className="info-tooltip-container">
    <svg
      className="info-icon"
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="16" x2="12" y2="12"></line>
      <line x1="12" y1="8" x2="12.01" y2="8"></line>
    </svg>
    <div className="info-tooltip-text">{text}</div>
  </div>
);

const SecureFileList = ({
  files,
  handleDelete,
  handleDownload,
  isDeleting,
}) => (
  <div className="list-section">
    <div className="list-title-container">
      <h3 className="list-title">Your Secure Files</h3>
      {/* --- FIX: The new info tooltip is placed here --- */}
      <InfoTooltip text="Files in this section are protected with Server Side Encryption. For enhanced durability, ENCRYPTED Tagged files are encrypted using AES-256 and Server Side which are replicated to a secondary storage at different region(country), which may incur higher costs." />
    </div>
    {files && files.length > 0 ? (
      <ul className="secure-file-list">
        {files.map((file) => (
          <li key={file.filename} className="file-list-item">
            <div className="file-info">
              <span className="file-name">{file.filename}</span>
              {file.is_encrypted && (
                <span className="encrypted-tag">Encrypted</span>
              )}
            </div>
            <div className="file-actions">
              {isDeleting === file.filename ? (
                <span className="deleting-indicator">Deleting...</span>
              ) : (
                <>
                  <button
                    onClick={() => handleDownload(file.filename)}
                    className="btn download-btn"
                  >
                    Download
                  </button>
                  <button
                    onClick={() => handleDelete(file.filename)}
                    className="btn danger-btn"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    ) : (
      <p className="empty-list-message">
        No secure files have been uploaded yet.
      </p>
    )}
  </div>
);

const API_BASE_URL = import.meta.env.DEV 
  ? 'http://localhost:8000/api'
  : 'https://zenith-backend-707i.onrender.com/api';
const handleResponse = async (response) => {
  if (!response.ok) throw await response.json();
  if (response.status === 204) return { success: true };
  const contentType = response.headers.get("content-type");
  return contentType?.includes("application/json") ? response.json() : {};
};
const status2FA = (token) =>
  fetch(`${API_BASE_URL}/2fa/status-2fa`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const enable2FA = (token) =>
  fetch(`${API_BASE_URL}/2fa/enable-2fa`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const finalize2FA = (token, code) =>
  fetch(`${API_BASE_URL}/2fa/finalize-2fa`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ code }),
  }).then(handleResponse);
const verify2FA = (token, code) =>
  fetch(`${API_BASE_URL}/2fa/verify-2fa`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ code }),
  }).then(handleResponse);
const disable2FA = (token) =>
  fetch(`${API_BASE_URL}/2fa/disable-2fa`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const listSecureFiles = (token) =>
  fetch(`${API_BASE_URL}/security/list-secure`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const deleteSecureFile = (filename, token) =>
  fetch(`${API_BASE_URL}/security/delete/${filename}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const getSecureDownloadUrl = (filename, token) =>
  fetch(`${API_BASE_URL}/security/download/${filename}`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(handleResponse);
const uploadSecureFile = (file, encrypt, token) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("encrypt_manual", encrypt);
  return fetch(`${API_BASE_URL}/security/upload-secure`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  }).then(handleResponse);
};

// --- MAIN COMPONENT ---

function SecurityPage() {
  const { token, user } = useAuth();
  const notifications = useNotifications();
  const [file, setFile] = useState(null);
  const [encrypt, setEncrypt] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [secureFiles, setSecureFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [twoFAStatus, setTwoFAStatus] = useState({
    enabled: false,
    verified: false,
    secret_exists: false,
  });
  const [qrCode, setQrCode] = useState(null);
  const [twoFACode, setTwoFACode] = useState("");
  const fileInputRef = useRef(null);
  const [showModal, setShowModal] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(null);
  const pollIntervalRef = useRef(null);

  const canAccessSecureArea = !twoFAStatus.enabled || twoFAStatus.verified;

  const fetchSecureFiles = useCallback(async () => {
    if (!token || !canAccessSecureArea) return [];
    try {
      const files = await listSecureFiles(token);
      setSecureFiles(files);
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
      } catch (err) {
        if (err.detail?.includes("2FA token verification is required")) {
          setTwoFAStatus({
            enabled: true,
            verified: false,
            secret_exists: true,
          });
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
      await uploadSecureFile(file, encrypt, token);
      notifications.info(`'${uploadedFileName}' accepted. Waiting for processing...`);
      pollIntervalRef.current = setInterval(async () => {
        const updatedFiles = await fetchSecureFiles();
        const processedFile = updatedFiles.find(
          (f) => f.filename === uploadedFileName
        );
        if (processedFile && typeof processedFile.is_encrypted === "boolean") {
          clearInterval(pollIntervalRef.current);
          notifications.success(`Processing for '${uploadedFileName}' complete.`);
        }
      }, 5000);
    } catch (err) {
      notifications.error(err.detail || "Secure upload failed.");
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    } finally {
      setIsUploading(false);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
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

  const handleDownload = async (filename) => {
    try {
      const { presigned_url } = await getSecureDownloadUrl(filename, token);
      window.open(presigned_url, "_blank");
    } catch (error) {
      notifications.error(error.detail || "Could not get download link.");
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
    .form-group input[type="file"] { color: #999; font-family: 'Inter', sans-serif; }
    .form-group input[type="file"]::file-selector-button { background-color: var(--primary-gold); color: #000; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; font-family: 'Inter', sans-serif; margin-right: 1rem; }
    .form-group input[type="file"]::file-selector-button:hover { background-color: var(--hover-gold); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(212, 175, 55, 0.2); }
    .checkbox-group { display: flex; align-items: center; gap: 0.5rem; }
    .btn { background-color: var(--primary-gold); color: #000; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; }
    .btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
    .btn.danger-btn { background-color: var(--danger-red); color: #fff; }
    .btn.danger-btn:hover { box-shadow: 0 6px 20px rgba(220, 53, 69, 0.3); }
    .btn.download-btn { background-color: var(--primary-blue); color: #fff; }
    .btn.download-btn:hover { box-shadow: 0 6px 20px rgba(0, 123, 255, 0.3); }
    .btn.success-btn { background-color: var(--success-green); color: #fff; }
    .btn.success-btn:hover { box-shadow: 0 6px 20px rgba(40, 167, 69, 0.3); }
    .btn:disabled { background-color: #444; color: #888; cursor: not-allowed; transform: none; box-shadow: none; }
    .list-title { font-size: 1.5rem; font-weight: 600; margin-top: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color); }
    .secure-file-list { list-style: none; padding: 0; }
    .file-list-item { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; padding: 1rem; background: #1c1c1c; border-radius: 8px; }
    .file-info { display: flex; align-items: center; }
    .file-name { font-weight: 500; }
    .file-actions { display: flex; gap: 0.5rem; min-width: 190px; justify-content: flex-end; }
    .encrypted-tag { background-color: #6a0dad; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-left: 12px; text-transform: uppercase; }
    .empty-list-message { color: var(--text-secondary); text-align: center; padding: 2rem; }
    .deleting-indicator { color: var(--danger-red); font-size: 0.9rem; font-style: italic; }
    .twofa-container { max-width: 500px; margin: 4rem auto; background: var(--content-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 2.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; }
    .twofa-title { font-size: 1.75rem; font-weight: 600; color: #fff; margin-top: 0; margin-bottom: 1rem; }
    .twofa-description { color: var(--text-secondary); margin-bottom: 2rem; line-height: 1.6; }
    .twofa-input { display: block; width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 1.5rem; border-radius: 8px; border: 1px solid var(--border-color); background: #111; color: var(--text-primary); font-size: 1.2rem; text-align: center; letter-spacing: 0.3em; }
    .confirm-modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; }
    .modal-content { background: #252525; padding: 2.5rem; border-radius: 12px; text-align: center; }
    .modal-content p { margin-bottom: 2rem; }
    .modal-buttons .btn { margin: 0 0.5rem; }

    /* --- FIX: Styles for the new info icon and tooltip --- */
    .list-title-container {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .info-tooltip-container {
      position: relative;
      display: inline-block;
      cursor: pointer;
    }
    .info-icon {
      color: var(--text-secondary);
    }
    .info-tooltip-text {
      visibility: hidden;
      width: 280px;
      background-color: #333;
      color: #fff;
      text-align: left;
      border-radius: 6px;
      padding: 10px;
      position: absolute;
      z-index: 1;
      bottom: 150%;
      left: 50%;
      margin-left: -140px; /* Use half of the width to center */
      opacity: 0;
      transition: opacity 0.3s;
      font-size: 0.85rem;
      font-weight: 400;
      line-height: 1.5;
    }
    .info-tooltip-container:hover .info-tooltip-text {
      visibility: visible;
      opacity: 1;
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
          <div className="form-group">
            <input ref={fileInputRef} type="file" onChange={handleFileChange} />
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
              className="btn"
            >
              {isUploading ? "Uploading..." : "Upload Secure File"}
            </button>
          </div>
        </div>
        <SecureFileList
          files={secureFiles}
          handleDelete={(filename) => {
            setFileToDelete(filename);
            setShowModal(true);
          }}
          handleDownload={handleDownload}
          isDeleting={isDeleting}
        />
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