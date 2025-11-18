import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { toast } from 'react-toastify';
import '../styles/home.css';

function HomePage() {
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const { user, login } = useAuth();
  const navigate = useNavigate();

  // If user is already logged in, redirect to dashboard
  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(formData.username, formData.password);
      toast.success('Login successful!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
      setIsLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
      }

      toast.success('Account created successfully! Please login.');
      setAuthMode('login');
      setFormData({ ...formData, password: '', confirmPassword: '' });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="landing-page-auth">
      {/* Left Side - Branding */}
      <div className="auth-branding">
        <div className="branding-content">
          <h1 className="brand-logo">Zenith</h1>
          <h2 className="brand-tagline">Optimize Your Cloud. Maximize Your Savings.</h2>
          <p className="brand-description">
            The intelligent cloud resource optimization platform that reduces costs by up to 60% 
            while improving performance across AWS, GCP, and Azure.
          </p>
          
          <div className="brand-features">
            <div className="brand-feature">
              <div className="feature-icon">💰</div>
              <div className="feature-content">
                <h4>Cost Savings</h4>
                <p>Save up to 60% on cloud costs</p>
              </div>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">⚡</div>
              <div className="feature-content">
                <h4>Performance</h4>
                <p>38% faster resource allocation</p>
              </div>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">🔒</div>
              <div className="feature-content">
                <h4>Security</h4>
                <p>Enterprise-grade protection</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Auth Form */}
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <h2>{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
            <p>{authMode === 'login' ? 'Sign in to your dashboard' : 'Start your free trial today'}</p>
          </div>

          {/* Tab Switcher */}
          <div className="auth-tabs">
            <button 
              className={`auth-tab ${authMode === 'login' ? 'active' : ''}`}
              onClick={() => setAuthMode('login')}
            >
              Login
            </button>
            <button 
              className={`auth-tab ${authMode === 'signup' ? 'active' : ''}`}
              onClick={() => setAuthMode('signup')}
            >
              Sign Up
            </button>
          </div>

          {/* Login Form */}
          {authMode === 'login' && (
            <form onSubmit={handleLogin} className="auth-form">
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  placeholder="Enter your username"
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="Enter your password"
                  required
                />
              </div>

              <button type="submit" className="btn-submit" disabled={isLoading}>
                {isLoading ? (
                  <span className="loading-spinner"></span>
                ) : (
                  'Sign In to Dashboard'
                )}
              </button>

              <p className="form-footer">
                Don't have an account? <button type="button" onClick={() => setAuthMode('signup')} className="link-btn">Sign Up</button>
              </p>
            </form>
          )}

          {/* Signup Form */}
          {authMode === 'signup' && (
            <form onSubmit={handleSignup} className="auth-form">
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="you@example.com"
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  placeholder="Choose a username"
                  required
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="At least 8 characters"
                  required
                />
              </div>

              <div className="form-group">
                <label>Confirm Password</label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  placeholder="Re-enter your password"
                  required
                />
              </div>

              <button type="submit" className="btn-submit" disabled={isLoading}>
                {isLoading ? (
                  <span className="loading-spinner"></span>
                ) : (
                  'Create Account'
                )}
              </button>

              <p className="form-footer">
                Already have an account? <button type="button" onClick={() => setAuthMode('login')} className="link-btn">Sign In</button>
              </p>
            </form>
          )}
        </div>

        <p className="auth-footer-text">&copy; 2025 Zenith. All rights reserved.</p>
      </div>
    </div>
  );
}

export default HomePage;
