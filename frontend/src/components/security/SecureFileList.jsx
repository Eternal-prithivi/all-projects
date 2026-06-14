import React from "react";
import { toast } from "react-toastify";
import { useAuth } from "../../context/AuthContext.jsx";
import { useConfirm } from "../../context/ConfirmContext.jsx";
import { getSecureDownloadUrl, deleteSecureFile } from "../../api.js";
import {
  IconDownload,
  IconTrash,
  IconAlert,
  IconLock,
} from "../dashboard/Icons.jsx";
import EmptyState from "../EmptyState.jsx";
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
  const { token } = useAuth();
  const { confirm } = useConfirm();

  const handleDownload = async (filename) => {
    try {
      const data = await getSecureDownloadUrl(filename, token);
      window.open(data.download_url, "_blank");
    } catch {
      toast.error("Could not get download link.");
    }
  };

  const handleDelete = async (filename) => {
    const ok = await confirm({
      title: "Delete secure file",
      message: `Delete ${filename} from the vault? This cannot be undone.`,
      confirmLabel: "Delete file",
      variant: "danger",
    });
    if (!ok) return;

    try {
      await deleteSecureFile(filename, token);
      await onFileDeleted();
      toast.success("Secure file deleted.");
    } catch (error) {
      toast.error(error?.detail || "Could not delete file. Please try again.");
    }
  };

  if (!files || files.length === 0) {
    return (
      <EmptyState
        icon={<IconLock aria-hidden="true" />}
        title="No secure files yet"
        message="Upload a file to the vault. Sensitive content can be auto-protected with SSE-S3 or browser encryption."
      />
    );
  }

  return (
    <div className="table-responsive-scroll">
    <table className="file-table data-card-table">
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
            <td data-label="Filename">{file.filename}</td>
            <td className="status-cell" data-label="Status">
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
            <td data-label="Size">{formatBytes(file.size_bytes)}</td>
            <td data-label="Upload Date">{new Date(file.upload_date).toLocaleString()}</td>
            <td className="actions-cell" data-label="Actions">
              <button
                type="button"
                onClick={() => handleDownload(file.filename)}
                className="action-btn"
              >
                <IconDownload />
              </button>
              <button
                type="button"
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
    </div>
  );
}

export default SecureFileList;
