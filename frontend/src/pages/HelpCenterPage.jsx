import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  FaSearch,
  FaQuestionCircle,
  FaChevronDown,
  FaChevronUp,
  FaRocket,
  FaDollarSign,
  FaServer,
  FaDatabase,
  FaShieldAlt,
  FaUser,
  FaEnvelope,
  FaLifeRing,
} from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import SupportTicketsSection from '../components/support/SupportTicketsSection.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { buildHelpFaqs, PATHS } from '../data/productFacts.js';
import '../styles/help-center.css';
import '../styles/support-tickets.css';

const TOPIC_TO_CATEGORY = {
  billing: 'billing',
  vms: 'vms',
  storage: 'storage',
  security: 'security',
  account: 'account',
  'getting-started': 'getting-started',
};

const HELP_TABS = [
  { id: 'articles', label: 'Help articles', icon: FaQuestionCircle },
  { id: 'tickets', label: 'My tickets', icon: FaLifeRing, requiresAuth: true },
];

const HelpCenterPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { token } = useAuth();
  const topicParam = searchParams.get('topic');
  const qParam = searchParams.get('q') || '';
  const tabParam = searchParams.get('tab');
  const activeTab = tabParam === 'tickets' && token ? 'tickets' : 'articles';

  const [searchQuery, setSearchQuery] = useState(qParam);
  const [selectedCategory, setSelectedCategory] = useState(
    TOPIC_TO_CATEGORY[topicParam] || 'all'
  );
  const [expandedQuestions, setExpandedQuestions] = useState(new Set());

  const faqs = useMemo(() => buildHelpFaqs(), []);

  useEffect(() => {
    if (qParam) setSearchQuery(qParam);
    if (topicParam && TOPIC_TO_CATEGORY[topicParam]) {
      setSelectedCategory(TOPIC_TO_CATEGORY[topicParam]);
    }
  }, [qParam, topicParam]);

  useEffect(() => {
    if (tabParam === 'tickets' && !token) {
      navigate(`/login?from=${encodeURIComponent('/help?tab=tickets')}`, { replace: true });
    }
  }, [tabParam, token, navigate]);

  const setActiveTab = useCallback(
    (tabId) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (tabId === 'articles') {
            next.delete('tab');
            next.delete('ref');
            next.delete('new');
          } else {
            next.set('tab', tabId);
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const openTicketsTab = useCallback(() => {
    if (!token) {
      navigate(`/login?from=${encodeURIComponent('/help?tab=tickets')}`);
      return;
    }
    setActiveTab('tickets');
  }, [token, navigate, setActiveTab]);

  const categories = [
    { id: 'all', name: 'All Topics', icon: FaQuestionCircle },
    { id: 'getting-started', name: 'Getting Started', icon: FaRocket },
    { id: 'billing', name: 'Billing & Plans', icon: FaDollarSign },
    { id: 'vms', name: 'Virtual Machines', icon: FaServer },
    { id: 'storage', name: 'Storage', icon: FaDatabase },
    { id: 'security', name: 'Security', icon: FaShieldAlt },
    { id: 'account', name: 'Account Management', icon: FaUser },
  ];

  const filteredFaqs = useMemo(() => {
    let filtered = faqs;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter((faq) => faq.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (faq) =>
          faq.question.toLowerCase().includes(query) ||
          faq.answer.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [faqs, searchQuery, selectedCategory]);

  const toggleQuestion = (id) => {
    setExpandedQuestions((prev) => {
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
    return categories.find((cat) => cat.id === categoryId)?.name || 'Unknown';
  };

  return (
    <MarketingPageLayout>
      <div className="help-center-page">
        {token && (
          <div className="help-context-banner reveal-item" role="navigation">
            <Link to={PATHS.dashboard}>← Back to dashboard</Link>
            {topicParam && activeTab === 'articles' && (
              <span className="help-context-banner__topic">
                Showing: {getCategoryName(TOPIC_TO_CATEGORY[topicParam] || topicParam)}
              </span>
            )}
          </div>
        )}

        <div className="help-header reveal-group">
          <div className="help-header-content">
            <h1 className="help-title reveal-item">
              <FaLifeRing className="title-icon" />
              Help &amp; Support
            </h1>
            <p className="help-subtitle reveal-item">
              Browse answers or open a support ticket — everything in one place
            </p>
          </div>
        </div>

        <nav className="help-hub-tabs reveal-item" aria-label="Help sections">
          {HELP_TABS.map((tab) => {
            const Icon = tab.icon;
            if (tab.requiresAuth && !token) return null;
            return (
              <button
                key={tab.id}
                type="button"
                className={`help-hub-tab ${activeTab === tab.id ? 'is-active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? 'page' : undefined}
              >
                <Icon aria-hidden />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {activeTab === 'tickets' && token ? (
          <div className="help-hub-panel reveal-item">
            <SupportTicketsSection />
          </div>
        ) : (
          <>
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

            <div className="help-categories reveal-item">
              {categories.map((category) => {
                const Icon = category.icon;
                return (
                  <button
                    key={category.id}
                    type="button"
                    onClick={() => setSelectedCategory(category.id)}
                    className={`category-button ${selectedCategory === category.id ? 'active' : ''}`}
                  >
                    <Icon className="category-icon" />
                    <span>{category.name}</span>
                  </button>
                );
              })}
            </div>

            <div className="help-content reveal-group">
              {filteredFaqs.length === 0 ? (
                <div className="no-results">
                  <FaQuestionCircle className="no-results-icon" />
                  <h3>No results found</h3>
                  <p>Try adjusting your search or browse all topics</p>
                  <div className="no-results-actions">
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery('');
                        setSelectedCategory('all');
                      }}
                      className="reset-button"
                    >
                      View All FAQs
                    </button>
                    <button type="button" onClick={openTicketsTab} className="contact-button-alt">
                      <FaEnvelope /> Open a ticket
                    </button>
                  </div>
                </div>
              ) : (
                <div className="faq-list">
                  {selectedCategory !== 'all' && (
                    <h2 className="category-heading">{getCategoryName(selectedCategory)}</h2>
                  )}

                  {filteredFaqs.map((faq) => (
                    <div key={faq.id} className="faq-item reveal-item">
                      <button
                        type="button"
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

            <div className="help-footer reveal-item">
              <div className="contact-support-card">
                <FaEnvelope className="contact-icon" />
                <h3>Still need help?</h3>
                <p>Can&apos;t find what you&apos;re looking for? Open a ticket or send us a message.</p>
                <div className="help-footer-actions">
                  <button type="button" onClick={openTicketsTab} className="contact-button">
                    {token ? 'My support tickets' : 'Sign in for tickets'}
                  </button>
                  <button type="button" onClick={() => navigate(PATHS.contact)} className="contact-button contact-button--secondary">
                    Contact form
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </MarketingPageLayout>
  );
};

export default HelpCenterPage;
