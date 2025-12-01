import React, { useState } from 'react';
import '../styles/decryption-modal.css';

const DecryptionPasswordModal = ({ file, onClose, onDecrypt }) => {
  const [password, setPassword] = useState('');
  const [isDecrypting, setIsDecrypting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!password) {
      setError('Please enter your encryption password');
      return;
    }

    setIsDecrypting(true);
    setError('');

    try {
      await onDecrypt(password);
      onClose();
    } catch (err) {
      setError(err.message || 'Incorrect password or decryption failed');
      setIsDecrypting(false);
    }
  };

  return (
    <div className="decryption-modal-overlay">
      <div className="decryption-modal">
        <div className="decryption-modal-header">
          <h2>🔓 Enter Decryption Password</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="decryption-modal-body">
          <div className="file-info">
            <p>File: <strong>{file.filename}</strong></p>
            <p className="encryption-info">
              🔒 This file is encrypted with client-side encryption
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Encryption Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError('');
                }}
                placeholder="Enter the password you used for encryption"
                className="password-input"
                autoFocus
              />
              {error && <p className="error-message">{error}</p>}
            </div>

            <div className="info-box">
              <p>
                ℹ️ This file was encrypted with <strong>AES-256</strong> using your password. 
                Only the correct password can decrypt it.
              </p>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-cancel" onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                className="btn-decrypt"
                disabled={isDecrypting || !password}
              >
                {isDecrypting ? 'Decrypting...' : 'Decrypt & Download'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default DecryptionPasswordModal;
