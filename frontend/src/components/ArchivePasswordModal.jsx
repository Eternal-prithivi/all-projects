import React, { useState } from "react";
import "../styles/decryption-modal.css";

const ACTION_COPY = {
  restore: {
    title: "Restore archived file",
    submit: "Restore",
    hint: "Enter the archive password you set when this file was moved to the replica vault.",
  },
  download: {
    title: "Download archived file",
    submit: "Continue download",
    hint: "Enter your archive password to download this file from the replica vault.",
  },
  delete: {
    title: "Delete archived file",
    submit: "Delete permanently",
    hint: "Enter your archive password to permanently delete this archived file.",
  },
};

export default function ArchivePasswordModal({
  file,
  action = "restore",
  onClose,
  onConfirm,
  isSubmitting = false,
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const copy = ACTION_COPY[action] || ACTION_COPY.restore;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("Please enter your archive password");
      return;
    }
    setError("");
    try {
      await onConfirm(password.trim());
    } catch (err) {
      setError(
        err?.detail
        || err?.message
        || "Incorrect archive password or action failed"
      );
    }
  };

  return (
    <div className="decryption-modal-overlay">
      <div className="decryption-modal">
        <div className="decryption-modal-header">
          <h2>{copy.title}</h2>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="decryption-modal-body">
          <div className="file-info">
            <p>
              File: <strong>{file?.filename}</strong>
            </p>
            <p className="encryption-info">{copy.hint}</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="archive-password-input">Archive password</label>
              <input
                id="archive-password-input"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
                placeholder="Password used when archiving"
                className="password-input"
                autoFocus
                autoComplete="current-password"
              />
              {error && <p className="error-message">{error}</p>}
            </div>

            <div className="info-box">
              <p>
                Zenith stores a secure hash of your archive password — the plain password is never saved.
              </p>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-cancel" onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                className={action === "delete" ? "btn-danger" : "btn-decrypt"}
                disabled={isSubmitting || !password.trim()}
              >
                {isSubmitting ? "Working…" : copy.submit}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
