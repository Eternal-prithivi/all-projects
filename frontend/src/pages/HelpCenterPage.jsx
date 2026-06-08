import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaSearch, FaQuestionCircle, FaChevronDown, FaChevronUp, FaRocket, FaDollarSign, FaServer, FaDatabase, FaShieldAlt, FaUser, FaEnvelope } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/help-center.css';

const HelpCenterPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedQuestions, setExpandedQuestions] = useState(new Set());

  const categories = [
    { id: 'all', name: 'All Topics', icon: FaQuestionCircle },
    { id: 'getting-started', name: 'Getting Started', icon: FaRocket },
    { id: 'billing', name: 'Billing & Plans', icon: FaDollarSign },
    { id: 'vms', name: 'Virtual Machines', icon: FaServer },
    { id: 'storage', name: 'Storage', icon: FaDatabase },
    { id: 'security', name: 'Security', icon: FaShieldAlt },
    { id: 'account', name: 'Account Management', icon: FaUser },
  ];

  const faqs = [
    // Getting Started
    {
      id: 1,
      category: 'getting-started',
      question: 'How do I get started with Zenith?',
      answer: 'Getting started is easy! First, create an account by clicking "Sign Up" on the homepage. Once registered, you\'ll be directed to your dashboard where you can choose a subscription plan. After selecting a plan, you can start creating VMs, uploading files, and optimizing your cloud resources immediately.'
    },
    {
      id: 2,
      category: 'getting-started',
      question: 'What cloud providers does Zenith support?',
      answer: 'Zenith supports the three major cloud providers: Amazon Web Services (AWS), Google Cloud Platform (GCP), and Microsoft Azure. Our platform intelligently recommends the best provider based on your workload requirements, budget, and performance needs.'
    },
    {
      id: 3,
      category: 'getting-started',
      question: 'Is there a free trial available?',
      answer: 'Yes! We offer a 14-day free trial with no credit card required. The trial includes access to basic features, allowing you to test VM creation, storage management, and cost analysis tools. You can upgrade to a paid plan anytime during or after the trial.'
    },
    {
      id: 4,
      category: 'getting-started',
      question: 'What are the system requirements?',
      answer: 'Zenith is a cloud-based platform accessible through any modern web browser (Chrome, Firefox, Safari, Edge). No software installation is required. For API access, we support standard REST APIs that work with any programming language.'
    },

    // Billing & Plans
    {
      id: 5,
      category: 'billing',
      question: 'What subscription plans are available?',
      answer: 'We offer three plans: Free (basic features, 1 VM, 5GB storage), Basic ($49/month, 5 VMs, 100GB storage, email support), and Pro ($149/month, unlimited VMs, 1TB storage, priority support, advanced analytics). All paid plans include cost optimization features and multi-cloud support.'
    },
    {
      id: 6,
      category: 'billing',
      question: 'How does billing work?',
      answer: 'Billing is monthly and processed automatically using your saved payment method. You can view your current usage, upcoming charges, and billing history in the Billing section of your dashboard. We send invoice emails before each billing cycle.'
    },
    {
      id: 7,
      category: 'billing',
      question: 'Can I change my plan anytime?',
      answer: 'Yes! You can upgrade or downgrade your plan at any time from the Settings page. Upgrades take effect immediately, while downgrades apply at the start of your next billing cycle. Prorated credits are applied when upgrading mid-cycle.'
    },
    {
      id: 8,
      category: 'billing',
      question: 'What payment methods do you accept?',
      answer: 'We accept all major credit cards (Visa, Mastercard, American Express), debit cards, and UPI payments through our secure payment gateway powered by Razorpay. All transactions are encrypted and PCI-DSS compliant.'
    },
    {
      id: 9,
      category: 'billing',
      question: 'How do I cancel my subscription?',
      answer: 'You can cancel your subscription anytime from Settings > Billing > Cancel Subscription. You\'ll retain access until the end of your current billing period. We don\'t offer refunds for partial months, but you can export all your data before cancellation.'
    },

    // Virtual Machines
    {
      id: 10,
      category: 'vms',
      question: 'How do I create a virtual machine?',
      answer: 'Navigate to the VM Cluster page in your dashboard and click "Request VM". Choose your VM type (Performance or Storage), configure specs (CPU, RAM, disk), and select your preferred cloud provider. The VM will be provisioned within 2-5 minutes.'
    },
    {
      id: 11,
      category: 'vms',
      question: 'What VM types are available?',
      answer: 'We offer two cluster types: Performance VMs (optimized for CPU-intensive workloads with e2-micro instances) and Storage VMs (optimized for data storage with larger disk sizes). Each type is configured for specific use cases to maximize cost efficiency.'
    },
    {
      id: 12,
      category: 'vms',
      question: 'How do I connect to my VM?',
      answer: 'After your VM is created, you\'ll receive SSH connection details in the VM details panel. Use any SSH client with the provided hostname, username, and SSH key. For Windows, we recommend PuTTY. For Mac/Linux, use the built-in terminal with the ssh command.'
    },
    {
      id: 13,
      category: 'vms',
      question: 'Can I stop and restart VMs?',
      answer: 'Yes! You can stop VMs when not in use to save costs. Stopped VMs retain all data but don\'t incur compute charges. Restart them anytime from the VM Cluster page. Note: You\'ll still be charged for disk storage while VMs are stopped.'
    },
    {
      id: 14,
      category: 'vms',
      question: 'How do I migrate VMs between cloud providers?',
      answer: 'Use our VM Migration feature to transfer VMs between AWS, GCP, and Azure. Select the source VM, choose the destination provider, and we\'ll handle the data transfer and reconfiguration. Migration typically takes 15-30 minutes depending on VM size.'
    },

    // Storage
    {
      id: 15,
      category: 'storage',
      question: 'How do I upload files to cloud storage?',
      answer: 'Go to the Storage page and click "Upload File". Drag and drop files or browse to select them. Our intelligent optimizer will recommend the best cloud provider (AWS S3, GCP Storage, or Azure Blob) based on file size, access frequency, and your budget preferences.'
    },
    {
      id: 16,
      category: 'storage',
      question: 'What is intelligent storage tiering?',
      answer: 'Our ML-based system automatically moves files between hot (frequent access), cool (occasional access), and archive (long-term) storage tiers based on usage patterns. This can reduce storage costs by up to 60% without manual intervention.'
    },
    {
      id: 17,
      category: 'storage',
      question: 'Is my data encrypted?',
      answer: 'Yes! All files are encrypted at rest using AES-256 encryption and in transit using TLS 1.3. For extra security, enable manual encryption on the Security page. Encrypted files require your password to decrypt and download.'
    },
    {
      id: 18,
      category: 'storage',
      question: 'What file size limits exist?',
      answer: 'File size limits depend on your plan: Free (100MB per file), Basic (1GB per file), Pro (10GB per file). For larger files, contact support for enterprise options. Total storage limits are 5GB (Free), 100GB (Basic), and 1TB (Pro).'
    },

    // Security
    {
      id: 19,
      category: 'security',
      question: 'How do I enable two-factor authentication (2FA)?',
      answer: 'Go to Settings > Security Settings and click "Enable 2FA". Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code to activate. You\'ll need this code along with your password for all future logins.'
    },
    {
      id: 20,
      category: 'security',
      question: 'What happens if I lose my 2FA device?',
      answer: 'If you lose access to your 2FA device, use your backup codes (provided during 2FA setup) to login. Each backup code can be used once. After logging in, you can disable 2FA and set it up again with a new device. Always save backup codes in a secure location.'
    },
    {
      id: 21,
      category: 'security',
      question: 'How do I manage active sessions?',
      answer: 'Visit Settings > Security Settings to view all active sessions with device info, location, and IP addresses. You can terminate any suspicious sessions remotely. Your current session is marked and cannot be terminated from the list.'
    },
    {
      id: 22,
      category: 'security',
      question: 'Are API keys secure?',
      answer: 'Yes! API keys are hashed before storage and only shown once during creation. Store them securely. You can revoke keys anytime from Settings > API Keys. All API requests are rate-limited and logged for security monitoring.'
    },

    // Account Management
    {
      id: 23,
      category: 'account',
      question: 'How do I change my password?',
      answer: 'Navigate to Settings > Security Settings and click "Change Password". Enter your current password and new password (minimum 8 characters). We recommend using a strong, unique password and enabling 2FA for extra security.'
    },
    {
      id: 24,
      category: 'account',
      question: 'Can I update my email address?',
      answer: 'Yes! Go to Profile page and click "Edit Profile". Update your email address and save. You\'ll receive a verification email at the new address. Click the link to confirm the change. Your old email will receive a notification about the update.'
    },
    {
      id: 25,
      category: 'account',
      question: 'How do I delete my account?',
      answer: 'To delete your account, contact support at aangatla957@gmail.com with your username and reason for deletion. We\'ll process the request within 7 days. Note: Account deletion is permanent and all data will be erased. Export any needed data before requesting deletion.'
    },
    {
      id: 26,
      category: 'account',
      question: 'How do I view my activity history?',
      answer: 'Go to Settings > Security Settings and scroll to the Activity Log section. You\'ll see a timeline of recent activities including logins, password changes, 2FA events, and profile updates. Each entry shows timestamp and IP address.'
    },
  ];

  // Filter FAQs based on search and category
  const filteredFaqs = useMemo(() => {
    let filtered = faqs;

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(faq => faq.category === selectedCategory);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(faq =>
        faq.question.toLowerCase().includes(query) ||
        faq.answer.toLowerCase().includes(query)
      );
    }

    return filtered;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- static FAQ list defined in component
  }, [searchQuery, selectedCategory]);

  const toggleQuestion = (id) => {
    setExpandedQuestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const getCategoryName = (categoryId) => {
    return categories.find(cat => cat.id === categoryId)?.name || 'Unknown';
  };

  return (
    <MarketingPageLayout>
    <div className="help-center-page">
      <div className="help-header reveal-group">
        <div className="help-header-content">
          <h1 className="help-title reveal-item">
            <FaQuestionCircle className="title-icon" />
            Help Center
          </h1>
          <p className="help-subtitle reveal-item">
            Find answers to common questions and learn how to get the most out of Zenith
          </p>
          <button type="button" onClick={() => navigate('/contact')} className="header-contact-button reveal-item">
            <FaEnvelope /> Contact Support
          </button>
        </div>
      </div>

      <div className="help-search-section reveal-item">
        <form
          role="search"
          className="search-container"
          onSubmit={(e) => e.preventDefault()}
        >
          <label htmlFor="help-search-input" className="sr-only">
            Search help articles
          </label>
          <span className="search-icon" aria-hidden="true">
            <FaSearch />
          </span>
          <input
            id="help-search-input"
            type="search"
            placeholder="Search for help articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
            autoComplete="off"
            enterKeyHint="search"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="clear-search"
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </form>
        {searchQuery.trim() && (
          <p className="search-results-hint" aria-live="polite">
            {filteredFaqs.length} {filteredFaqs.length === 1 ? 'result' : 'results'}
          </p>
        )}
      </div>

      {/* Category Filters */}
      <div className="help-categories reveal-item">
        {categories.map(category => {
          const Icon = category.icon;
          return (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`category-button ${selectedCategory === category.id ? 'active' : ''}`}
            >
              <Icon className="category-icon" />
              <span>{category.name}</span>
            </button>
          );
        })}
      </div>

      {/* FAQ List */}
      <div className="help-content reveal-group">
        {filteredFaqs.length === 0 ? (
          <div className="no-results">
            <FaQuestionCircle className="no-results-icon" />
            <h3>No results found</h3>
            <p>Try adjusting your search or browse all topics</p>
            <div className="no-results-actions">
              <button onClick={() => { setSearchQuery(''); setSelectedCategory('all'); }} className="reset-button">
                View All FAQs
              </button>
              <button onClick={() => navigate('/contact')} className="contact-button-alt">
                <FaEnvelope /> Contact Support
              </button>
            </div>
          </div>
        ) : (
          <div className="faq-list">
            {selectedCategory !== 'all' && (
              <h2 className="category-heading">{getCategoryName(selectedCategory)}</h2>
            )}
            
            {filteredFaqs.map(faq => (
              <div key={faq.id} className="faq-item reveal-item">
                <button
                  onClick={() => toggleQuestion(faq.id)}
                  className="faq-question"
                >
                  <span className="question-text">{faq.question}</span>
                  {expandedQuestions.has(faq.id) ? (
                    <FaChevronUp className="chevron" />
                  ) : (
                    <FaChevronDown className="chevron" />
                  )}
                </button>
                
                {expandedQuestions.has(faq.id) && (
                  <div className="faq-answer">
                    <p>{faq.answer}</p>
                    {selectedCategory === 'all' && (
                      <span className="faq-category-tag">
                        {getCategoryName(faq.category)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contact Support */}
      <div className="help-footer reveal-item">
        <div className="contact-support-card">
          <FaEnvelope className="contact-icon" />
          <h3>Still need help?</h3>
          <p>Can't find what you're looking for? Our support team is here to help!</p>
          <button onClick={() => navigate('/contact')} className="contact-button">
            Contact Support
          </button>
        </div>
      </div>
    </div>
    </MarketingPageLayout>
  );
};

export default HelpCenterPage;
