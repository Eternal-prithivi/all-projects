import React from 'react';
import HeaderToolbarActions from '../layout/HeaderToolbarActions.jsx';
import HeaderGlobalSearchTrigger from '../layout/HeaderGlobalSearchTrigger.jsx';
import ZenithLogo from '../brand/ZenithLogo.jsx';

function Header() {
  return (
    <header className="dashboard-header">
      <div className="header-brand header-brand-zenith">
        <ZenithLogo size={28} />
        <span className="header-brand-text">Zenith</span>
        <span className="header-brand-badge">Cloud</span>
      </div>

      <HeaderGlobalSearchTrigger />

      <HeaderToolbarActions
        notificationViewAllPath="/dashboard/notifications"
        showSearchTrigger={false}
      />
    </header>
  );
}

export default Header;
