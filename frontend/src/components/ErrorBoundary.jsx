import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/error-pages.css';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(_error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(_error, errorInfo) {
    // Log error to console or error reporting service
    console.error('Error caught by boundary:', _error, errorInfo);
    
    // You can also log to an error reporting service like Sentry
    // logErrorToService(error, errorInfo);
    
    this.setState({
      error: _error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-page">
          <div className="error-container">
            {/* Error Code */}
            <div className="error-code error-code-react">⚠️</div>

            {/* Error Title */}
            <h1 className="error-title">Oops! Something Broke</h1>

            {/* Error Description */}
            <p className="error-description">
              A client-side error occurred. Don't worry, it's not your fault!
              <br />
              Try refreshing the page or going back home.
            </p>

            {/* Illustration */}
            <div className="error-illustration">
              <svg
                width="300"
                height="200"
                viewBox="0 0 300 200"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Broken code illustration */}
                <g transform="translate(80, 50)">
                  {/* Code window */}
                  <rect x="0" y="0" width="140" height="100" rx="4" fill="#1a1f35" opacity="0.3" />
                  <rect x="2" y="2" width="136" height="96" rx="3" fill="var(--gold-primary)" opacity="0.1" />
                  
                  {/* Code lines */}
                  <line x1="10" y1="20" x2="50" y2="20" stroke="var(--gold-primary)" strokeWidth="2" opacity="0.6" />
                  <line x1="10" y1="30" x2="80" y2="30" stroke="var(--gold-primary)" strokeWidth="2" opacity="0.6" />
                  <line x1="10" y1="40" x2="40" y2="40" stroke="var(--gold-primary)" strokeWidth="2" opacity="0.6" />
                  
                  {/* Error line */}
                  <line x1="10" y1="50" x2="90" y2="50" stroke="#ef4444" strokeWidth="2" />
                  <line x1="10" y1="50" x2="90" y2="50" stroke="#ef4444" strokeWidth="4" opacity="0.3" />
                  
                  {/* More code lines */}
                  <line x1="10" y1="60" x2="70" y2="60" stroke="var(--gold-primary)" strokeWidth="2" opacity="0.6" />
                  <line x1="10" y1="70" x2="60" y2="70" stroke="var(--gold-primary)" strokeWidth="2" opacity="0.6" />
                  
                  {/* Error indicator */}
                  <circle cx="100" cy="50" r="8" fill="#ef4444" opacity="0.8" />
                  <text x="97" y="54" fill="#fff" fontSize="12" fontWeight="bold">!</text>
                </g>

                {/* Crack effect */}
                <path
                  d="M 150 0 L 150 200"
                  stroke="#ef4444"
                  strokeWidth="2"
                  strokeDasharray="5,5"
                  opacity="0.3"
                />
              </svg>
            </div>

            {/* Action Buttons */}
            <div className="error-actions">
              <button onClick={() => window.location.reload()} className="error-btn secondary">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 4v6h-6M1 20v-6h6" />
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                Refresh Page
              </button>
              <button onClick={this.handleReset} className="error-btn primary">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9 22 9 12 15 12 15 22" />
                </svg>
                Go Home
              </button>
            </div>

            {/* Error Details (development only) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="error-details">
                <details open>
                  <summary>Error Stack Trace (Development Only)</summary>
                  <div className="error-details-content">
                    <p><strong>Error Message:</strong></p>
                    <pre>{this.state.error.toString()}</pre>
                    
                    {this.state.errorInfo && (
                      <>
                        <p><strong>Component Stack:</strong></p>
                        <pre>{this.state.errorInfo.componentStack}</pre>
                      </>
                    )}
                  </div>
                </details>
              </div>
            )}

            {/* Help Section */}
            <div className="error-help">
              <p>Need assistance?</p>
              <Link to="/contact" className="error-help-link">
                Contact Support →
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
