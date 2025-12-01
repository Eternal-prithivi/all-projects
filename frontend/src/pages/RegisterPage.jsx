import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { registerUser } from '../api';
import Footer from '../components/layout/Footer.jsx';
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
    <>
      <div className="register-page-container">
        <div className="register-form-container">
          <form onSubmit={handleSubmit} aria-label="Registration form">
          <h2>Create Account</h2>
          <div className="input-group">
            <label htmlFor="reg-username">Username</label>
            <input 
              type="text" 
              id="reg-username" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
              aria-required="true"
              autoComplete="username"
              aria-describedby="username-help"
              minLength={3}
            />
            <small id="username-help" className="form-help" style={{fontSize: '0.85rem', color: '#888'}}>At least 3 characters</small>
          </div>
          <div className="input-group">
            <label htmlFor="reg-email">Email</label>
            <input 
              type="email" 
              id="reg-email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              aria-required="true"
              autoComplete="email"
              aria-describedby="email-help"
            />
            <small id="email-help" className="form-help" style={{fontSize: '0.85rem', color: '#888'}}>We'll never share your email</small>
          </div>
          <div className="input-group">
            <label htmlFor="reg-password">Password</label>
            <input 
              type="password" 
              id="reg-password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              minLength="8" 
              aria-required="true"
              autoComplete="new-password"
              aria-describedby="password-help"
            />
            <small id="password-help" className="form-help" style={{fontSize: '0.85rem', color: '#888'}}>Minimum 8 characters</small>
          </div>
          <button type="submit" className="register-button" aria-label="Submit registration form">Create Account</button>
          <div className="message-area">
            {message && <p className="success-message" role="status" aria-live="polite">{message}</p>}
            {error && <p className="error-message" role="alert" aria-live="assertive">{error}</p>}
          </div>
          <div className="navigation-link">
            <p>Already have an account? <Link to="/login">Log in</Link></p>
          </div>
        </form>
      </div>
    </div>
    <Footer />
  </>
  );
}

export default RegisterPage;

