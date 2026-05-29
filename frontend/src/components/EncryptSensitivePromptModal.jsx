import React from "react";
import "../styles/encryption-modal.css";

/**
 * Shown after upload when sensitive data is detected — user must choose to encrypt.
 */
const EncryptSensitivePromptModal = ({ file, scanReasons = [], onEncrypt, onDismiss }) => {
  const reasonText =
    scanReasons.length > 0
      ? scanReasons.map((r) => r.replace(/_/g, " ")).join(", ")
      : "sensitive patterns";

  return (
    <div className="encryption-modal-overlay">
      <div className="encryption-modal encrypt-prompt-modal">
        <div className="encryption-modal-header">
          <h2>Sensitive data detected</h2>
          <button type="button" className="close-btn" onClick={onDismiss}>
            ×
          </button>
        </div>
        <div className="encryption-modal-body">
          <div className="file-info-banner sensitive-alert">
            <p>
              <strong>{file?.filename || "This file"}</strong> was scanned and may contain
              security-related data ({reasonText}).
            </p>
            <p>
              For redundancy and protection, encrypt it before it is stored in your secure
              vault. Zenith never sees your client-side encryption password.
            </p>
          </div>
          <div className="encrypt-prompt-actions">
            <button type="button" className="btn-cancel" onClick={onDismiss}>
              Not now
            </button>
            <button type="button" className="btn-encrypt" onClick={onEncrypt}>
              Encrypt this file
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EncryptSensitivePromptModal;
