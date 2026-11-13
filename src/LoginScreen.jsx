import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BrandWordmark } from './dashboard/components/BrandWordmark.jsx';
import { authenticate, authenticateWithGoogle, registerAccount, DEMO_ACCOUNTS } from './auth/authService.js';
import './styles/login.css';

// SVG Icons matching Miora's clean stroke style
const Icons = {
  user: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
  stethoscope: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4.5 3v5a4.5 4.5 0 0 0 9 0V3" />
      <path d="M9 12.5v4a3.5 3.5 0 0 0 7 0v-2.5" />
      <circle cx="16" cy="14" r="2.5" fill="currentColor" fillOpacity="0.15" />
      <path d="M3 3h3M12 3h3" />
    </svg>
  ),
  mail: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4.5" width="18" height="15" rx="2.5" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  ),
  lock: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4.5" y="11" width="15" height="10" rx="2.5" />
      <path d="M7.5 11V7a4.5 4.5 0 0 1 9 0v4" />
    </svg>
  ),
  eye: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  eyeOff: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
      <line x1="2" y1="2" x2="22" y2="22" />
    </svg>
  ),
  arrowRight: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  ),
  check: (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 6.5 4.8 9.2 10 3" />
    </svg>
  ),
  google: (
    <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  ),
};

export function LoginScreen() {
  const navigate = useNavigate();

  // Active tab: 'signin' | 'create'
  const [activeTab, setActiveTab] = useState('signin');

  // Selected role: 'patient' (default) | 'doctor'
  const [selectedRole, setSelectedRole] = useState('patient');

  // Form fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Interaction feedback states
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Auto-fill demo account helper
  const handleSelectDemo = (role) => {
    setSelectedRole(role);
    setErrorMessage('');
    setSuccessMessage('');
    if (role === 'patient') {
      setEmail(DEMO_ACCOUNTS.patient.email);
      setPassword(DEMO_ACCOUNTS.patient.password);
    } else {
      setEmail(DEMO_ACCOUNTS.doctor.email);
      setPassword(DEMO_ACCOUNTS.doctor.password);
    }
  };

  // Sign In submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    setIsLoading(true);

    try {
      if (activeTab === 'signin') {
        const result = await authenticate({
          email,
          password,
          selectedRole,
        });
        navigate(result.redirectUrl);
      } else {
        const result = await registerAccount({
          name,
          email,
          password,
          role: selectedRole,
        });
        navigate(result.redirectUrl);
      }
    } catch (err) {
      setErrorMessage(err.message || 'An error occurred during authentication.');
    } finally {
      setIsLoading(false);
    }
  };

  // Google OAuth flow
  const handleGoogleAuth = async () => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsLoading(true);

    try {
      const result = await authenticateWithGoogle(selectedRole);
      navigate(result.redirectUrl);
    } catch (err) {
      setErrorMessage(err.message || 'Google sign-in failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Forgot Password handler
  const handleForgotPassword = () => {
    if (!email) {
      setErrorMessage('Please enter your email address to receive password reset instructions.');
      return;
    }
    setErrorMessage('');
    setSuccessMessage(`Password reset link sent to ${email}. Please check your inbox.`);
  };

  return (
    <div className="login-page-root">
      {/* Background Flowing Wave Shapes */}
      <div className="login-bg-decor" aria-hidden="true">
        <svg
          className="login-bg-svg"
          viewBox="0 0 1024 768"
          preserveAspectRatio="none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Top subtle organic wave flowing behind logo and upper card */}
          <path
            d="M 0 0 L 1024 0 L 1024 160 C 940 190, 780 120, 640 100 C 460 75, 340 150, 180 125 C 90 110, 30 70, 0 85 Z"
            fill="url(#topWaveGrad)"
            opacity="0.8"
          />

          {/* Large soft blush sweeping wave from top-left curving down behind card */}
          <path
            d="M 0 135 C 160 170, 310 80, 520 60 C 740 40, 890 130, 1024 95 L 1024 0 L 0 0 Z"
            fill="url(#blushWashTop)"
            opacity="0.5"
          />

          {/* Right side delicate organic contour waves */}
          <path
            d="M 940 0 C 980 140, 920 280, 980 430 C 1010 500, 1015 620, 1024 768 L 1024 0 Z"
            fill="url(#rightDecorWave1)"
            opacity="0.55"
          />
          <path
            d="M 970 200 C 990 320, 960 480, 1024 640 L 1024 200 Z"
            fill="url(#rightDecorWave2)"
            opacity="0.45"
          />

          {/* Soft bottom-right wave curve */}
          <path
            d="M 880 768 C 930 710, 970 680, 1024 690 L 1024 768 Z"
            fill="#fae5ee"
            opacity="0.6"
          />

          <defs>
            <linearGradient id="topWaveGrad" x1="0" y1="0" x2="1" y2="0.8">
              <stop offset="0%" stopColor="#fdeaf0" />
              <stop offset="45%" stopColor="#fbe2ec" />
              <stop offset="100%" stopColor="#fdf1f5" />
            </linearGradient>
            <linearGradient id="blushWashTop" x1="0" y1="0" x2="0.9" y2="1">
              <stop offset="0%" stopColor="#fae0e9" />
              <stop offset="60%" stopColor="#fcecf1" />
              <stop offset="100%" stopColor="#fcf4f6" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="rightDecorWave1" x1="0.8" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fbe3ec" />
              <stop offset="60%" stopColor="#f8d6e2" />
              <stop offset="100%" stopColor="#fae4ee" />
            </linearGradient>
            <linearGradient id="rightDecorWave2" x1="0.5" y1="0.2" x2="1" y2="0.9">
              <stop offset="0%" stopColor="#f9d9e5" />
              <stop offset="100%" stopColor="#f6cedd" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="login-container">
        {/* ================================================================
            Left Section – Branding and Illustration
            ================================================================ */}
        <section className="login-left-col" aria-label="Miora brand presentation">
          <div className="login-left-top">
            {/* Upper-left branding */}
            <div className="login-branding">
              <Link to="/" className="login-logo-link" aria-label="Miora Home">
                <span className="login-brand-wordmark">
                  <svg className="login-brand-m" viewBox="0 0 50 30" fill="none" aria-hidden="true">
                    <path
                      d="M30.8 1.5H36.6L28.8 21.8H26.8L32.8 3.4C32.9 2.5 32.2 2.0 30.8 2.0Z"
                      fill="currentColor"
                    />
                    <path
                      d="M33.2 2.0L19.4 21.8C16.2 25.8 12.1 27.2 7.8 26.6C4.2 26.1 2.0 23.8 2.2 21.2C2.3 19.9 3.4 19.4 4.2 19.9C4.9 20.4 4.8 21.5 4.0 21.9"
                      stroke="currentColor"
                      strokeWidth="1.35"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle cx="3.3" cy="21.0" r="1.45" fill="currentColor" />
                    <path
                      d="M44.8 1.5H49.4L42.2 20.9C42.0 21.4 42.5 21.7 43.7 21.7H44.1V22.4H36.8V21.7H37.6C38.8 21.7 39.3 21.4 39.6 20.8L45.6 4.0L28.4 21.9H27.1L46.0 2.2C45.5 1.8 45.1 1.6 44.8 1.5Z"
                      fill="currentColor"
                    />
                  </svg>
                  <span className="login-brand-script">iora</span>
                </span>
              </Link>

              {/* Exact Tagline */}
              <p className="login-tagline">
                Maternal Emotional<br />
                Intelligence
              </p>

              {/* Thin, subtle pink divider */}
              <div className="login-brand-divider" aria-hidden="true" />
            </div>

            {/* Main Editorial Heading */}
            <h1 className="login-heading">
              Compassionate<br />
              Support for Your<br />
              <em>Postpartum Journey</em>
            </h1>

            {/* Supporting Copy */}
            <p className="login-subtext">
              Screen, understand and get personalised support for your emotional wellbeing.
            </p>
          </div>

          {/* Mother and Baby Illustration in normal flex flow (never overlaps text) */}
          
        </section>

        {/* ================================================================
            Right Section – Authentication Card
            ================================================================ */}
        <section className="login-right-col" aria-label="Sign in credentials">
          <div className="login-auth-card">
            {/* Tabs: Sign In / Create Account */}
            <div className="login-tabs-bar" role="tablist" aria-label="Authentication modes">
              <button
                type="button"
                role="tab"
                id="tab-signin"
                aria-selected={activeTab === 'signin'}
                aria-controls="panel-auth"
                className={`login-tab-btn ${activeTab === 'signin' ? 'is-active' : ''}`}
                onClick={() => {
                  setActiveTab('signin');
                  setErrorMessage('');
                  setSuccessMessage('');
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                role="tab"
                id="tab-create"
                aria-selected={false}
                aria-controls="panel-auth"
                className="login-tab-btn"
                onClick={() => {
                  navigate('/create-account');
                }}
              >
                Create Account
              </button>
            </div>

            {/* Header Titles */}
            <header className="login-card-header">
              <h2 className="login-card-title">
                {activeTab === 'signin' ? 'Welcome Back' : 'Create Your Account'}
              </h2>
              <p className="login-card-subtext">
                {activeTab === 'signin'
                  ? 'Sign in to continue your Miora journey.'
                  : 'Join Miora for compassionate, personalised support.'}
              </p>
            </header>

            {/* Alerts */}
            {errorMessage && (
              <div className="login-alert login-alert-error" role="alert">
                <span>{errorMessage}</span>
              </div>
            )}
            {successMessage && (
              <div className="login-alert login-alert-success" role="status">
                <span>{successMessage}</span>
              </div>
            )}

            {/* Main Form */}
            <form id="panel-auth" onSubmit={handleSubmit} noValidate>
              {/* Role Selection */}
              <div className="login-role-section">
                <label className="login-role-label" id="role-select-label">
                  I am a<span className="login-required-star">*</span>
                </label>
                <div
                  className="login-role-grid"
                  role="radiogroup"
                  aria-labelledby="role-select-label"
                >
                  {/* Patient Card (Selected by default) */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedRole === 'patient'}
                    tabIndex={0}
                    className={`login-role-card ${selectedRole === 'patient' ? 'is-selected' : ''}`}
                    onClick={() => {
                      setSelectedRole('patient');
                      setErrorMessage('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === ' ' || e.key === 'Enter') {
                        e.preventDefault();
                        setSelectedRole('patient');
                      }
                    }}
                  >
                    <span className="login-role-icon">{Icons.user}</span>
                    <span className="login-role-content">
                      <strong className="login-role-title">Patient</strong>
                      <span className="login-role-desc">For new mothers and postpartum care</span>
                    </span>
                    <span className="login-role-indicator">
                      {selectedRole === 'patient' ? (
                        <span className="login-indicator-checked">{Icons.check}</span>
                      ) : (
                        <span className="login-indicator-empty" />
                      )}
                    </span>
                  </button>

                  {/* Doctor Card */}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={selectedRole === 'doctor'}
                    tabIndex={0}
                    className={`login-role-card ${selectedRole === 'doctor' ? 'is-selected' : ''}`}
                    onClick={() => {
                      setSelectedRole('doctor');
                      setErrorMessage('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === ' ' || e.key === 'Enter') {
                        e.preventDefault();
                        setSelectedRole('doctor');
                      }
                    }}
                  >
                    <span className="login-role-icon">{Icons.stethoscope}</span>
                    <span className="login-role-content">
                      <strong className="login-role-title">Doctor</strong>
                      <span className="login-role-desc">For healthcare professionals</span>
                    </span>
                    <span className="login-role-indicator">
                      {selectedRole === 'doctor' ? (
                        <span className="login-indicator-checked">{Icons.check}</span>
                      ) : (
                        <span className="login-indicator-empty" />
                      )}
                    </span>
                  </button>
                </div>

                {/* Quick 1-Click Demo Fill */}
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: '#7a6870', fontWeight: '500' }}>Try Demo:</span>
                  <button
                    type="button"
                    onClick={() => handleSelectDemo('patient')}
                    style={{
                      fontSize: '12px',
                      padding: '4px 12px',
                      background: selectedRole === 'patient' ? '#fdeaf0' : '#f5f5f7',
                      color: selectedRole === 'patient' ? '#c73566' : '#555',
                      border: '1px solid ' + (selectedRole === 'patient' ? '#f4a6c0' : '#dcdce0'),
                      borderRadius: '16px',
                      cursor: 'pointer',
                      fontWeight: selectedRole === 'patient' ? '600' : '500',
                    }}
                  >
                    Patient (Amara)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectDemo('doctor')}
                    style={{
                      fontSize: '12px',
                      padding: '4px 12px',
                      background: selectedRole === 'doctor' ? '#fdeaf0' : '#f5f5f7',
                      color: selectedRole === 'doctor' ? '#c73566' : '#555',
                      border: '1px solid ' + (selectedRole === 'doctor' ? '#f4a6c0' : '#dcdce0'),
                      borderRadius: '16px',
                      cursor: 'pointer',
                      fontWeight: selectedRole === 'doctor' ? '600' : '500',
                    }}
                  >
                    Doctor (Dr. Elena)
                  </button>
                </div>
              </div>

              {/* Name field (for Create Account mode) */}
              {activeTab === 'create' && (
                <div className="login-form-group">
                  <label className="login-field-label" htmlFor="user-name">
                    Full Name
                  </label>
                  <div className="login-input-wrap">
                    <span className="login-input-icon">{Icons.user}</span>
                    <input
                      id="user-name"
                      type="text"
                      className="login-text-input"
                      placeholder="Enter your full name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                    />
                  </div>
                </div>
              )}

              {/* Email Address */}
              <div className="login-form-group">
                <label className="login-field-label" htmlFor="user-email">
                  Email Address
                </label>
                <div className="login-input-wrap">
                  <span className="login-input-icon">{Icons.mail}</span>
                  <input
                    id="user-email"
                    type="email"
                    className="login-text-input"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div className="login-form-group">
                <label className="login-field-label" htmlFor="user-password">
                  Password
                </label>
                <div className="login-input-wrap">
                  <span className="login-input-icon">{Icons.lock}</span>
                  <input
                    id="user-password"
                    type={showPassword ? 'text' : 'password'}
                    className="login-text-input"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={activeTab === 'signin' ? 'current-password' : 'new-password'}
                    required
                  />
                  <button
                    type="button"
                    className="login-visibility-btn"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? Icons.eyeOff : Icons.eye}
                  </button>
                </div>
              </div>

              {/* Forgot Password? (Right-aligned) */}
              {activeTab === 'signin' && (
                <div className="login-forgot-row">
                  <button
                    type="button"
                    className="login-forgot-link"
                    onClick={handleForgotPassword}
                  >
                    Forgot Password?
                  </button>
                </div>
              )}

              {/* Primary Action Button */}
              <button
                type="submit"
                className="login-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="login-spinner" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>{activeTab === 'signin' ? 'Sign In' : 'Create Account'}</span>
                    <span>{Icons.arrowRight}</span>
                  </>
                )}
              </button>

              {/* Divider with 'or' */}
              <div className="login-divider-row" aria-hidden="true">
                <span className="login-divider-line" />
                <span className="login-divider-text">or</span>
                <span className="login-divider-line" />
              </div>

              {/* Continue with Google */}
              <button
                type="button"
                className="login-google-btn"
                onClick={handleGoogleAuth}
                disabled={isLoading}
              >
                {Icons.google}
                <span>Continue with Google</span>
              </button>

              {/* Bottom Switch Link */}
              <div className="login-bottom-link" style={{ textAlign: 'center', marginTop: '16px' }}>
                <span style={{ fontSize: '13px', color: '#62555a' }}>Don't have an account? </span>
                <Link to="/create-account" style={{ color: '#c73566', fontWeight: '600', fontSize: '13px' }}>
                  Create Account
                </Link>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}

export default LoginScreen;
