import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { registerUser } from '../api';
import '../styles/register.css';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');
    setError('');
    try {
      const userData = { username, email, password };
      const response = await registerUser(userData);
      setMessage(response.message);
    } catch (err) {
      setError(err.detail || 'An error occurred during registration.');
    }
  };

  return (
    <div className="register-page-container">
      <div className="register-form-container">
        <form onSubmit={handleSubmit}>
          <h2>Create Account</h2>
          <div className="input-group">
            <label htmlFor="reg-username">Username</label>
            <input type="text" id="reg-username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="input-group">
            <label htmlFor="reg-email">Email</label>
            <input type="email" id="reg-email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="input-group">
            <label htmlFor="reg-password">Password</label>
            <input type="password" id="reg-password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength="8" />
          </div>
          <button type="submit" className="register-button">Create Account</button>
          <div className="message-area">
            {message && <p className="success-message">{message}</p>}
            {error && <p className="error-message">{error}</p>}
          </div>
          <div className="navigation-link">
            <p>Already have an account? <Link to="/login">Log in</Link></p>
          </div>
        </form>
      </div>
    </div>
  );
}

export default RegisterPage;

