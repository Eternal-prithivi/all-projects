import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { loginUser } from '../api';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/login.css';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    try {
      const credentials = { username, password };
      const data = await loginUser(credentials);
      login(data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.detail || 'An error occurred during login.');
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-form-container">
        <form onSubmit={handleSubmit}>
          <h2>Login</h2>
          <div className="input-group">
            <label htmlFor="login-username">Username</label>
            <input type="text" id="login-username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="input-group">
            <label htmlFor="login-password">Password</label>
            <input type="password" id="login-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="login-button">Log In</button>
          {error && <p className="error-message">{error}</p>}
          <div className="navigation-link">
            <p>Not registered yet? <Link to="/register">Create an account</Link></p>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
