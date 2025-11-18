import React from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { getDownloadUrl, deleteFile } from '../../api.js';
// This is the corrected import path
import { IconDownload, IconTrash } from '../dashboard/Icons.jsx';
import '../../styles/file-list.css';

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function FileList({ files, onFileDeleted }) {
  const { token } = useAuth();

  const handleDownload = async (filename) => {
    try {
      const data = await getDownloadUrl(filename, token);
      window.open(data.download_url, '_blank');
    } catch (error) {
      alert('Could not get download link.');
    }
  };

  const handleDelete = async (filename) => {
    if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
      try {
        await deleteFile(filename, token);
        onFileDeleted();
      } catch (error) {
        alert('Could not delete file.');
      }
    }
  };

  if (!files || files.length === 0) {
    return <p className="empty-message">No files uploaded yet.</p>;
  }

  return (
    <table className="file-table">
      <thead>
        <tr>
          <th>Filename</th>
          <th>Size</th>
          <th>Last Modified</th>
          <th>Storage Class</th>
          <th className="actions-header">Actions</th>
        </tr>
      </thead>
      <tbody>
        {files.map((file) => (
          <tr key={file.key}>
            <td>{file.filename}</td>
            <td>{formatBytes(file.size_bytes)}</td>
            <td>{new Date(file.last_modified).toLocaleString()}</td>
            <td>{file.storage_class}</td>
            <td className="actions-cell">
              <button onClick={() => handleDownload(file.filename)} className="action-btn">
                <IconDownload />
              </button>
              <button onClick={() => handleDelete(file.filename)} className="action-btn delete-btn">
                <IconTrash />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default FileList;
