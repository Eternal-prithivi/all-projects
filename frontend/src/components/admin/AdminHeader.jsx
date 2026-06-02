import React from 'react';
import HeaderToolbarActions from '../layout/HeaderToolbarActions.jsx';
import HeaderGlobalSearchTrigger from '../layout/HeaderGlobalSearchTrigger.jsx';
import '../../styles/admin-layout.css';

const AdminHeader = () => (
  <header className="admin-header">
    <div className="admin-header-left">
      <h1>Platform Administration</h1>
    </div>

    <div className="admin-header-center">
      <HeaderGlobalSearchTrigger className="admin-header-search" />
    </div>

    <HeaderToolbarActions
      notificationViewAllPath="/admin/notifications"
      showSearchTrigger={false}
      className="header-actions admin-header-toolbar"
    />
  </header>
);

export default AdminHeader;
