import React from "react";
import { useAuth } from "../../context/AuthContext.jsx";
import { getSecureDownloadUrl, deleteSecureFile } from "../../api.js";
import {
  IconDownload,
  IconTrash,
  IconAlert,
  IconLock,
} from "../dashboard/Icons.jsx";
import "../../styles/file-list.css";

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

function SecureFileList({ files, onFileDeleted }) {
  // Add onFileDeleted
  const { token } = useAuth();

  const handleDownload = async (filename) => {
    try {
      const data = await getSecureDownloadUrl(filename, token);
      window.open(data.download_url, "_blank");
    } catch {
      alert("Could not get download link.");
    }
  };

  const handleDelete = async (filename) => {
    if (
      window.confirm(
        `Are you sure you want to delete this secure file: ${filename}?`
      )
    ) {
      try {
        await deleteSecureFile(filename, token);
        await onFileDeleted(); 
      } catch (_error) {
        alert(_error.detail || "Could not delete file. Please try again.");
      }
    }
  };

  if (!files || files.length === 0) {
    return (
      <p className="empty-message">No secure files have been uploaded yet.</p>
    );
  }

  return (
    <table className="file-table">
      <thead>
        <tr>
          <th>Filename</th>
          <th>Status</th>
          <th>Size</th>
          <th>Upload Date</th>
          <th className="actions-header">Actions</th>
        </tr>
      </thead>
      <tbody>
        {files.map((file) => (
          <tr key={file.filename}>
            <td>{file.filename}</td>
            <td className="status-cell">
              {file.is_encrypted ? (
                <span className="encrypted-flag" title="Encrypted">
                  <IconLock /> Encrypted
                </span>
              ) : file.is_sensitive ? (
                <span
                  className="sensitive-flag"
                  title="Sensitive Data Detected"
                >
                  <IconAlert /> Sensitive
                </span>
              ) : (
                <span>Normal</span>
              )}
            </td>
            <td>{formatBytes(file.size_bytes)}</td>
            <td>{new Date(file.upload_date).toLocaleString()}</td>
            <td className="actions-cell">
              <button
                onClick={() => handleDownload(file.filename)}
                className="action-btn"
              >
                <IconDownload />
              </button>
              <button
                onClick={() => handleDelete(file.filename)}
                className="action-btn delete-btn"
              >
                <IconTrash />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default SecureFileList;
