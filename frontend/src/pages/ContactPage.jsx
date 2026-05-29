import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import { getValidationErrorMessage, validateContactForm } from '../utils/formValidation.js';
import '../styles/contact.css';

function ContactPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: 'general',
    message: ''
  });
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const validation = validateContactForm(formData);
  const isSubmitDisabled = loading || !validation.isValid;

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setFieldErrors(validation.errors);

    if (!validation.isValid) {
      toast.error(getValidationErrorMessage(validation.errors) || 'Please fix the highlighted fields.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/contact/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        toast.success('Message sent successfully! We\'ll get back to you soon.');
        setFormData({ name: '', email: '', subject: 'general', message: '' });
        setTimeout(() => navigate('/'), 2000);
      } else {
        throw new Error('Failed to send message');
      }
    } catch (error) {
      toast.error('Failed to send message. Please try again.');
      console.error('Contact form error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <MarketingPageLayout>
      <div className="contact-page">
        <div className="contact-container">
          <div className="contact-header reveal-group">
            <div className="reveal-item">
              <p className="marketing-page-hero__eyebrow">Support</p>
              <h1>Get in Touch</h1>
              <p>Have a question or need support? We're here to help.</p>
            </div>
          </div>

          <div className="contact-content reveal-group">
            {/* Left: Contact Info */}
            <div className="contact-info reveal-stagger">
              <div className="info-card reveal-item">
                <div className="info-icon">📧</div>
                <h3>Email Us</h3>
                <p>support@rajverse.me</p>
                <span className="info-note">We'll respond within 24 hours</span>
              </div>

              <div className="info-card reveal-item">
                <div className="info-icon">📞</div>
                <h3>Call Us</h3>
                <p>+91 88077 30239</p>
                <span className="info-note">Available 9 AM - 6 PM IST</span>
              </div>

              <div className="info-card reveal-item">
                <div className="info-icon">📚</div>
                <h3>Documentation</h3>
                <p>Check our help center</p>
                <span className="info-note">Most questions answered here</span>
              </div>
            </div>

            {/* Right: Contact Form */}
            <div className="contact-form-wrapper reveal-item reveal-item--delay-2">
              <form className="contact-form" onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="name">Name *</label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="John Doe"
                    required
                    aria-invalid={Boolean(fieldErrors.name)}
                    aria-describedby={fieldErrors.name ? 'contact-name-error' : undefined}
                  />
                  {fieldErrors.name && (
                    <p className="form-field-error" id="contact-name-error" role="alert">
                      {fieldErrors.name}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="email">Email *</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="john@example.com"
                    required
                    aria-invalid={Boolean(fieldErrors.email)}
                    aria-describedby={fieldErrors.email ? 'contact-email-error' : undefined}
                  />
                  {fieldErrors.email && (
                    <p className="form-field-error" id="contact-email-error" role="alert">
                      {fieldErrors.email}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="subject">Subject *</label>
                  <select
                    id="subject"
                    name="subject"
                    className="zenith-select"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                    aria-invalid={Boolean(fieldErrors.subject)}
                    aria-describedby={fieldErrors.subject ? 'contact-subject-error' : undefined}
                  >
                    <option value="general">General Inquiry</option>
                    <option value="support">Technical Support</option>
                    <option value="billing">Billing Question</option>
                    <option value="feature">Feature Request</option>
                    <option value="bug">Report a Bug</option>
                  </select>
                  {fieldErrors.subject && (
                    <p className="form-field-error" id="contact-subject-error" role="alert">
                      {fieldErrors.subject}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="message">Message *</label>
                  <textarea
                    id="message"
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    placeholder="Tell us how we can help..."
                    rows="6"
                    required
                    aria-invalid={Boolean(fieldErrors.message)}
                    aria-describedby={fieldErrors.message ? 'contact-message-error' : undefined}
                  />
                  {fieldErrors.message && (
                    <p className="form-field-error" id="contact-message-error" role="alert">
                      {fieldErrors.message}
                    </p>
                  )}
                </div>

                <button 
                  type="submit" 
                  className="submit-button"
                  disabled={isSubmitDisabled}
                >
                  {loading ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </MarketingPageLayout>
  );
}

export default ContactPage;
