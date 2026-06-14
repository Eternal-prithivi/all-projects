import React from 'react';
import { toast } from 'react-toastify';
import { useAuth } from '../../context/AuthContext.jsx';
import { useConfirm } from '../../context/ConfirmContext.jsx';
import { getDownloadUrl, deleteFile } from '../../api.js';
import { IconDownload, IconTrash, IconHardDrive } from '../dashboard/Icons.jsx';
import EmptyState from '../EmptyState.jsx';
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
  const { confirm } = useConfirm();

  const handleDownload = async (filename) => {
    try {
      const data = await getDownloadUrl(filename, token);
      window.open(data.download_url, '_blank');
    } catch {
      toast.error('Could not get download link.');
    }
  };

  const handleDelete = async (filename) => {
    const ok = await confirm({
      title: 'Delete file',
      message: `Delete ${filename}? This cannot be undone.`,
      confirmLabel: 'Delete file',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await deleteFile(filename, token);
      onFileDeleted();
      toast.success('File deleted.');
    } catch {
      toast.error('Could not delete file.');
    }
  };

  if (!files || files.length === 0) {
    return (
      <EmptyState
        icon={<IconHardDrive aria-hidden="true" />}
        title="No files yet"
        message="Upload a file above to see it listed here with storage class and actions."
      />
    );
  }

  return (
    <div className="table-responsive-scroll">
    <table className="file-table data-card-table">
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
            <td data-label="Filename">{file.filename}</td>
            <td data-label="Size">{formatBytes(file.size_bytes)}</td>
            <td data-label="Last Modified">{new Date(file.last_modified).toLocaleString()}</td>
            <td data-label="Storage Class">{file.storage_class}</td>
            <td className="actions-cell" data-label="Actions">
              <button type="button" onClick={() => handleDownload(file.filename)} className="action-btn">
                <IconDownload />
              </button>
              <button type="button" onClick={() => handleDelete(file.filename)} className="action-btn delete-btn">
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

export default FileList;
