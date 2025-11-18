import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import '../styles/profile.css';

const ProfilePage = () => {
  const { user } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || 'user@example.com',
    fullName: user?.fullName || '',
    phone: user?.phone || '',
    company: user?.company || '',
    role: user?.role || 'Admin',
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: API call to update profile
    toast.success('Profile updated successfully!');
    setIsEditing(false);
  };

  const handleCancel = () => {
    setFormData({
      username: user?.username || '',
      email: user?.email || 'user@example.com',
      fullName: user?.fullName || '',
      phone: user?.phone || '',
      company: user?.company || '',
      role: user?.role || 'Admin',
    });
    setIsEditing(false);
  };

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
            <div className="profile-picture-large">
              {formData.username?.substring(0, 2).toUpperCase() || 'U'}
            </div>
            <div className="profile-picture-actions">
              <button className="btn-upload">Upload Photo</button>
              <button className="btn-remove">Remove</button>
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
                  name="fullName"
                  value={formData.fullName}
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
                <div className="stat-value">12</div>
                <div className="stat-label">Total VMs Created</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">💾</div>
              <div className="stat-details">
                <div className="stat-value">2.4 TB</div>
                <div className="stat-label">Storage Used</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">💰</div>
              <div className="stat-details">
                <div className="stat-value">$847</div>
                <div className="stat-label">Total Spend</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">📅</div>
              <div className="stat-details">
                <div className="stat-value">6 months</div>
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
              <button className="btn-danger">Delete Account</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
