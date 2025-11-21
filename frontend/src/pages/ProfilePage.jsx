import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from "../hooks/useNotifications";
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/profile.css';

const ProfilePage = () => {
  const { user, token, logout } = useAuth();
  const notifications = useNotifications();
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
    company: '',
    role: 'Admin',
    profile_picture: null,
  });

  useEffect(() => {
    fetchProfileData();
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await apiClient.put('/profile/me', {
        username: formData.username,
        email: formData.email,
        full_name: formData.full_name,
        phone: formData.phone,
        company: formData.company
      });
      
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
      const response = await apiClient.post('/profile/picture', formDataObj, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      notifications.success('Profile picture uploaded successfully!');
      fetchProfileData();
    } catch (error) {
      notifications.error('Failed to upload profile picture');
    }
  };

  const handleRemovePicture = async () => {
    try {
      await apiClient.delete('/profile/picture');
      notifications.success('Profile picture removed successfully!');
      fetchProfileData();
    } catch (error) {
      notifications.error('Failed to remove profile picture');
    }
  };

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      '⚠️ WARNING: This will permanently delete your account and all associated data including VMs, files, and settings. This action cannot be undone. Are you absolutely sure?'
    );
    
    if (!confirmed) return;

    const doubleConfirm = window.confirm(
      'This is your last chance. Type "DELETE" in the next prompt to confirm account deletion.'
    );
    
    if (!doubleConfirm) return;

    const finalConfirmation = prompt('Type "DELETE" (in capital letters) to permanently delete your account:');
    
    if (finalConfirmation !== 'DELETE') {
      notifications.error('Account deletion cancelled - confirmation text did not match');
      return;
    }

    try {
      await apiClient.delete('/profile/account');
      notifications.success('Account deleted successfully. Redirecting...');
      
      // Log out after 2 seconds
      setTimeout(() => {
        logout();
        window.location.href = '/';
      }, 2000);
    } catch (error) {
      notifications.error('Failed to delete account');
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading profile..." />;
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h2>Profile Settings</h2>
        <p>Manage your account information and preferences</p>
      </div>

      <div className="profile-content">
        {/* Profile Picture Section */}
        <div className="profile-card">
          <h3>Profile Picture</h3>
          <div className="profile-picture-section">
            <div className="picture-container">
              {formData.profile_picture ? (
                <img src={formData.profile_picture} alt="Profile" className="profile-picture" />
              ) : (
                <div className="profile-picture-placeholder">
                  {formData.username?.charAt(0).toUpperCase() || 'U'}
                </div>
              )}
            </div>
            <div className="profile-picture-actions">
              <label htmlFor="picture-upload" className="btn-upload">Upload Photo</label>
              <input 
                id="picture-upload" 
                type="file" 
                accept="image/*" 
                onChange={handleUploadPicture}
                style={{ display: 'none' }}
              />
              <button className="btn-remove" onClick={handleRemovePicture} type="button">Remove</button>
              <p className="hint-text">JPG, GIF or PNG. Max size of 2MB</p>
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
          
          <form onSubmit={handleSubmit}>
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
                />
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
                />
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
                />
              </div>

              <div className="form-group">
                <label>Phone Number</label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  disabled={!isEditing}
                  className="form-input"
                  placeholder="+1 (555) 000-0000"
                />
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
                />
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
                <button type="submit" className="btn-save">
                  Save Changes
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
              <div className="stat-icon">🖥️</div>
              <div className="stat-details">
                <div className="stat-value">{stats.total_vms_created}</div>
                <div className="stat-label">Total VMs Created</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">💾</div>
              <div className="stat-details">
                <div className="stat-value">{stats.storage_used_tb.toFixed(2)} TB</div>
                <div className="stat-label">Storage Used</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">💰</div>
              <div className="stat-details">
                <div className="stat-value">${stats.total_spend.toFixed(2)}</div>
                <div className="stat-label">Total Spend</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">📅</div>
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
              <button className="btn-danger" onClick={handleDeleteAccount}>Delete Account</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
