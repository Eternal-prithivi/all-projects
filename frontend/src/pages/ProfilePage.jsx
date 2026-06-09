// =============================================================================
// PAGE: ProfilePage.jsx  (513 lines)
// ROUTE: /dashboard/profile
// PURPOSE: User profile management — display name, bio, avatar upload, change password,
//          view active sessions, revoke sessions, view activity log, delete account
// API: Uses apiClient → /api/profile/me, /api/profile/update, /api/profile/change-password,
//      /api/profile/sessions, /api/profile/activity-log, /api/profile/delete-account, /api/profile/avatar
// CONTEXTS: AuthContext (current user), useNotifications hook
// DO NOT:
//   - Show raw hashed_password in any field — backend strips it but double-check
//   - Allow deleting the current session from sessions list — that logs the user out immediately
//   - Skip password confirmation on delete-account — it's a destructive action
// =============================================================================
import React, { useMemo, useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from "../hooks/useNotifications";
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  IconClock,
  IconDollarSign,
  IconHardDrive,
  IconServer,
} from '../components/dashboard/Icons.jsx';
import {
  getValidationErrorMessage,
  validateProfileForm,
  validateRecoveryContactsForm,
} from '../utils/formValidation';
import '../styles/profile.css';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';

const ProfilePage = () => {
  const { token, logout, refreshUser } = useAuth();
  const notifications = useNotifications();
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    total_vms_created: 0,
    storage_used_tb: 0,
    total_spend: 0,
    member_since: 'Recent'
  });
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    phone: '',
    recovery_phone: '',
    recovery_email: '',
    company: '',
    role: 'Admin',
    profile_picture: null,
  });
  const [showDeleteAccountModal, setShowDeleteAccountModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  const profileValidation = useMemo(
    () => validateProfileForm({
      username: formData.username,
      email: formData.email,
      fullName: formData.full_name,
      company: formData.company,
    }),
    [formData]
  );

  const recoveryValidation = useMemo(
    () => validateRecoveryContactsForm({
      recoveryEmail: formData.recovery_email,
      phone: formData.phone,
      recoveryPhone: formData.recovery_phone,
    }),
    [formData]
  );

  useEffect(() => {
    fetchProfileData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload profile when token changes
  }, [token]);

  const fetchProfileData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch profile
      const profileResponse = await apiClient.get('/profile/me');
      const profileData = profileResponse.data;
      
      setFormData({
        username: profileData.username || '',
        email: profileData.email || '',
        full_name: profileData.full_name || '',
        phone: profileData.phone || '',
        recovery_phone: profileData.recovery_phone || '',
        recovery_email: profileData.recovery_email || '',
        company: profileData.company || '',
        role: profileData.role || 'Admin',
        profile_picture: profileData.profile_picture || null,
      });

      // Fetch stats
      const statsResponse = await apiClient.get('/profile/stats');
      setStats(statsResponse.data);
      
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      notifications.error('Failed to load profile data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e, fieldsOnly = null, validationResult = profileValidation) => {
    e.preventDefault();

    if (!validationResult.isValid) {
      notifications.error(getValidationErrorMessage(validationResult.errors));
      return;
    }

    const payload = fieldsOnly || {
      username: formData.username,
      email: formData.email,
      full_name: formData.full_name,
      phone: formData.phone,
      recovery_phone: formData.recovery_phone,
      recovery_email: formData.recovery_email,
      company: formData.company,
    };
    try {
      await apiClient.put('/profile/me', payload);
      
      notifications.success('Profile updated successfully!');
      setIsEditing(false);
      fetchProfileData();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to update profile');
    }
  };

  const handleCancel = () => {
    fetchProfileData();
    setIsEditing(false);
  };

  const handleUploadPicture = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      notifications.error('File size must be less than 2MB');
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      notifications.error('Please upload an image file');
      return;
    }

    const formDataObj = new FormData();
    formDataObj.append('file', file);

    try {
      await apiClient.post('/profile/picture', formDataObj, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      notifications.success('Profile picture uploaded successfully!');
      await fetchProfileData();
      await refreshUser();
    } catch (error) {
      const detail = error.response?.data?.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : detail?.message || 'Failed to upload profile picture';
      notifications.error(message);
    } finally {
      event.target.value = '';
    }
  };

  const handleRemovePicture = async () => {
    try {
      await apiClient.delete('/profile/picture');
      notifications.success('Profile picture removed successfully!');
      await fetchProfileData();
      await refreshUser();
    } catch (error) {
      const detail = error.response?.data?.detail;
      notifications.error(
        typeof detail === 'string' ? detail : 'Failed to remove profile picture'
      );
    }
  };

  const closeDeleteAccountModal = () => {
    if (isDeletingAccount) return;
    setShowDeleteAccountModal(false);
    setDeleteConfirmText('');
  };

  const handleConfirmDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE' || isDeletingAccount) return;

    setIsDeletingAccount(true);
    try {
      await apiClient.delete('/profile/account');
      setShowDeleteAccountModal(false);
      notifications.success('Account deleted successfully. Redirecting...');

      setTimeout(() => {
        logout();
        window.location.href = '/';
      }, 2000);
    } catch (error) {
      const detail = error.response?.data?.detail;
      notifications.error(
        typeof detail === 'string' ? detail : 'Failed to delete account',
      );
      setIsDeletingAccount(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading profile..." />;
  }

  return (
    <div className="profile-page">
      <PageHeader
        kicker="Account"
        title="Profile"
        subtitle="Manage your account information and preferences"
        onRefresh={() =>
          runPageRefresh(fetchProfileData, {
            loadingMessage: 'Refreshing profile…',
            successMessage: 'Profile page refreshed.',
            errorMessage: 'Failed to refresh profile.',
          })
        }
        refreshing={pageRefreshing || isLoading}
      />

      <div className="profile-content">
        {/* Profile Picture Section */}
        <div className="profile-card profile-card--avatar">
          <h3>Profile Picture</h3>
          <div className="profile-picture-section">
            <div className="picture-container">
              {formData.profile_picture ? (
                <img
                  src={formData.profile_picture}
                  alt={`${formData.username || 'User'} profile`}
                  className="profile-picture"
                />
              ) : (
                <div className="profile-picture-placeholder" aria-hidden="true">
                  {formData.username?.charAt(0).toUpperCase() || 'U'}
                </div>
              )}
            </div>
            <div className="profile-picture-actions">
              <p className="profile-picture-lead">
                Add a photo so your team can recognize you across Zenith.
              </p>
              <div className="profile-picture-buttons">
                <label htmlFor="picture-upload" className="btn-upload">
                  Upload photo
                </label>
                <input
                  id="picture-upload"
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={handleUploadPicture}
                  className="profile-picture-input"
                />
                {formData.profile_picture && (
                  <button
                    className="btn-remove"
                    onClick={handleRemovePicture}
                    type="button"
                  >
                    Remove
                  </button>
                )}
              </div>
              <p className="hint-text profile-picture-hint">
                JPG, PNG, GIF or WebP · max 2&nbsp;MB
              </p>
            </div>
          </div>
        </div>

        {/* Personal Information */}
        <div className="profile-card">
          <div className="card-header">
            <h3>Personal Information</h3>
            {!isEditing && (
              <button className="btn-edit" onClick={() => setIsEditing(true)}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5z"/>
                </svg>
                Edit
              </button>
            )}
          </div>
          
          <form onSubmit={(e) => handleSubmit(e, null, profileValidation)}>
            <div className="form-grid">
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  aria-invalid={isEditing && !!profileValidation.errors.username}
                  aria-describedby={isEditing && profileValidation.errors.username ? 'profile-username-error' : undefined}
                />
                {isEditing && profileValidation.errors.username && (
                  <p id="profile-username-error" className="form-field-error">{profileValidation.errors.username}</p>
                )}
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  aria-invalid={isEditing && !!profileValidation.errors.email}
                  aria-describedby={isEditing && profileValidation.errors.email ? 'profile-email-error' : undefined}
                />
                {isEditing && profileValidation.errors.email && (
                  <p id="profile-email-error" className="form-field-error">{profileValidation.errors.email}</p>
                )}
              </div>

              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="Enter your full name"
                  aria-invalid={isEditing && !!profileValidation.errors.full_name}
                  aria-describedby={isEditing && profileValidation.errors.full_name ? 'profile-full-name-error' : undefined}
                />
                {isEditing && profileValidation.errors.full_name && (
                  <p id="profile-full-name-error" className="form-field-error">{profileValidation.errors.full_name}</p>
                )}
              </div>

              <div className="form-group">
                <label>Company</label>
                <input
                  type="text"
                  name="company"
                  value={formData.company}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="Your company name"
                  aria-invalid={isEditing && !!profileValidation.errors.company}
                  aria-describedby={isEditing && profileValidation.errors.company ? 'profile-company-error' : undefined}
                />
                {isEditing && profileValidation.errors.company && (
                  <p id="profile-company-error" className="form-field-error">{profileValidation.errors.company}</p>
                )}
              </div>

              <div className="form-group">
                <label>Role</label>
                <input
                  type="text"
                  name="role"
                  value={formData.role}
                  disabled
                  className="form-input"
                />
              </div>
            </div>

            {isEditing && (
              <div className="form-actions">
                <button type="submit" className="btn-save" disabled={!profileValidation.isValid}>
                  Save Changes
                </button>
                <button type="button" className="btn-cancel" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            )}
          </form>
        </div>

        <div className="profile-card">
          <div className="card-header">
            <h3>Password recovery</h3>
            {!isEditing && (
              <button className="btn-edit" onClick={() => setIsEditing(true)} type="button">
                Edit
              </button>
            )}
          </div>
          <p className="hint-text recovery-intro">
            These contacts are used only for forgot-password. The reset link is sent to your recovery email when set;
            SMS codes go to your mobile (or alternate mobile). Use the same email or username on the forgot-password page.
          </p>
          <form
            onSubmit={(e) =>
              handleSubmit(e, {
                phone: formData.phone,
                recovery_phone: formData.recovery_phone,
                recovery_email: formData.recovery_email,
              }, recoveryValidation)
            }
          >
            {isEditing && recoveryValidation.errors.form && (
              <p className="form-field-error form-field-error--block">{recoveryValidation.errors.form}</p>
            )}
            <div className="form-grid">
              <div className="form-group form-group-full">
                <label>Recovery email (forgot password)</label>
                <input
                  type="email"
                  name="recovery_email"
                  value={formData.recovery_email}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="alternate@example.com"
                  aria-invalid={isEditing && !!recoveryValidation.errors.recovery_email}
                  aria-describedby={isEditing && recoveryValidation.errors.recovery_email ? 'profile-recovery-email-error' : undefined}
                />
                {isEditing && recoveryValidation.errors.recovery_email && (
                  <p id="profile-recovery-email-error" className="form-field-error">{recoveryValidation.errors.recovery_email}</p>
                )}
                <p className="hint-text">If set, reset links are sent here only—not your login email.</p>
              </div>

              <div className="form-group">
                <label>Mobile number (SMS reset)</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="+919876543210"
                  aria-invalid={isEditing && !!recoveryValidation.errors.phone}
                  aria-describedby={isEditing && recoveryValidation.errors.phone ? 'profile-phone-error' : undefined}
                />
                {isEditing && recoveryValidation.errors.phone && (
                  <p id="profile-phone-error" className="form-field-error">{recoveryValidation.errors.phone}</p>
                )}
              </div>

              <div className="form-group">
                <label>Alternate mobile (optional)</label>
                <input
                  type="tel"
                  name="recovery_phone"
                  value={formData.recovery_phone}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="+919876543211"
                  aria-invalid={isEditing && !!recoveryValidation.errors.recovery_phone}
                  aria-describedby={isEditing && recoveryValidation.errors.recovery_phone ? 'profile-recovery-phone-error' : undefined}
                />
                {isEditing && recoveryValidation.errors.recovery_phone && (
                  <p id="profile-recovery-phone-error" className="form-field-error">{recoveryValidation.errors.recovery_phone}</p>
                )}
                <p className="hint-text">Used if primary mobile is empty. Include country code (+91, +1, …).</p>
              </div>
            </div>

            {isEditing && (
              <div className="form-actions">
                <button type="submit" className="btn-save" disabled={!recoveryValidation.isValid}>
                  Save recovery contacts
                </button>
                <button type="button" className="btn-cancel" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            )}
          </form>
        </div>

        {/* Account Statistics */}
        <div className="profile-card">
          <h3>Account Statistics</h3>
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-icon"><IconServer aria-hidden="true" /></div>
              <div className="stat-details">
                <div className="stat-value">{stats.total_vms_created}</div>
                <div className="stat-label">Total VMs Created</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon"><IconHardDrive aria-hidden="true" /></div>
              <div className="stat-details">
                <div className="stat-value">
                  {stats.storage_used_tb >= 0.01
                    ? `${stats.storage_used_tb.toFixed(2)} TB`
                    : `${(stats.storage_used_tb * 1024).toFixed(2)} GB`}
                </div>
                <div className="stat-label">Storage Used</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon"><IconDollarSign aria-hidden="true" /></div>
              <div className="stat-details">
                <div className="stat-value">${stats.total_spend.toFixed(2)}</div>
                <div className="stat-label">Monthly Spend</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon"><IconClock aria-hidden="true" /></div>
              <div className="stat-details">
                <div className="stat-value">{stats.member_since}</div>
                <div className="stat-label">Member Since</div>
              </div>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="profile-card danger-zone">
          <h3>Danger Zone</h3>
          <div className="danger-actions">
            <div className="danger-item">
              <div>
                <h4>Delete Account</h4>
                <p>Permanently delete your account and all associated data</p>
              </div>
              <button
                type="button"
                className="btn-danger"
                onClick={() => setShowDeleteAccountModal(true)}
              >
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </div>

      {showDeleteAccountModal && (
        <div
          className="delete-account-modal-overlay"
          role="presentation"
          onClick={closeDeleteAccountModal}
        >
          <div
            className="delete-account-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-account-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 id="delete-account-title">Delete account permanently?</h4>
            <p className="delete-account-modal-warning">
              This will permanently delete your account and all associated data including VMs,
              files, and settings. This action cannot be undone.
            </p>
            <label className="delete-account-modal-label" htmlFor="delete-confirm-input">
              Type <strong>DELETE</strong> to confirm
            </label>
            <input
              id="delete-confirm-input"
              type="text"
              className="delete-account-modal-input"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="DELETE"
              autoComplete="off"
              autoFocus
              disabled={isDeletingAccount}
            />
            <div className="delete-account-modal-actions">
              <button
                type="button"
                className="delete-account-modal-cancel"
                onClick={closeDeleteAccountModal}
                disabled={isDeletingAccount}
              >
                Cancel
              </button>
              <button
                type="button"
                className="delete-account-modal-confirm"
                onClick={handleConfirmDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || isDeletingAccount}
              >
                {isDeletingAccount ? 'Deleting…' : 'Delete my account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfilePage;
