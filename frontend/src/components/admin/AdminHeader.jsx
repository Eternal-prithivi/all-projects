import React from 'react';
import HeaderToolbarActions from '../layout/HeaderToolbarActions.jsx';
import '../../styles/admin-layout.css';

const AdminHeader = () => (
  <header className="admin-header">
    <div className="admin-header-left">
      <h1>Platform Administration</h1>
    </div>
    <HeaderToolbarActions
      notificationViewAllPath="/admin/notifications"
      showSearchTrigger
      className="admin-header-right header-actions"
    />
  </header>
);

export default AdminHeader;
