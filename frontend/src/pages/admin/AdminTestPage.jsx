import React, { useState } from 'react';
import api from '../../api';
import { useAuth } from '../../context/AuthContext';

const AdminTestPage = () => {
  const { user } = useAuth();
  const [testResults, setTestResults] = useState({});
  const [loading, setLoading] = useState(false);

  const runTests = async () => {
    setLoading(true);
    const results = {};

    // Test 1: Check user object
    results.user = user;
    results.userRole = user?.role;
    results.isAdmin = user?.role === 'admin';

    // Test 2: Check token
    results.token = localStorage.getItem('authToken')?.substring(0, 20) + '...';

    // Test 3: Test /me endpoint
    try {
      const meRes = await api.get('/users/me');
      results.meEndpoint = { success: true, data: meRes.data };
    } catch (error) {
      results.meEndpoint = { success: false, error: error.response?.data || error.message };
    }

    // Test 4: Test admin dashboard endpoint
    try {
      const dashboardRes = await api.get('/admin/dashboard');
      results.adminDashboard = { success: true, data: dashboardRes.data };
    } catch (error) {
      results.adminDashboard = { success: false, error: error.response?.data || error.message };
    }

    // Test 5: Test admin users endpoint
    try {
      const usersRes = await api.get('/admin/users');
      results.adminUsers = { success: true, count: usersRes.data.users?.length };
    } catch (error) {
      results.adminUsers = { success: false, error: error.response?.data || error.message };
    }

    setTestResults(results);
    setLoading(false);
  };

  return (
    <div style={{ padding: '20px', color: '#fff' }}>
      <h1>Admin Portal Diagnostics</h1>
      
      <button 
        onClick={runTests}
        disabled={loading}
        style={{
          padding: '10px 20px',
          background: '#ffd700',
          color: '#000',
          border: 'none',
          borderRadius: '5px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: '16px',
          fontWeight: 'bold'
        }}
      >
        {loading ? 'Running Tests...' : 'Run Diagnostic Tests'}
      </button>

      {Object.keys(testResults).length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h2>Test Results:</h2>
          <pre style={{ 
            background: '#1a1a2e', 
            padding: '15px', 
            borderRadius: '5px',
            overflow: 'auto',
            maxHeight: '600px'
          }}>
            {JSON.stringify(testResults, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default AdminTestPage;
