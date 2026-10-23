import { useState, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import {
  apiUrl,
  setUserLoginToken,
  clearUserLoginToken,
  getActiveProjectId,
} from '../config';
import type { GitHubUser } from '../config';

interface GitHubAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: GitHubUser | null;
  onAuthSuccess?: (user: GitHubUser) => void;
}

export function GitHubAuthModal({
  isOpen,
  onClose,
  currentUser,
  onAuthSuccess,
}: GitHubAuthModalProps) {
  const [tab, setTab] = useState<'oauth' | 'pat' | 'demo'>('oauth');
  const [patToken, setPatToken] = useState<string>('');
  const [demoUsername, setDemoUsername] = useState<string>('muneeb-sawez');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [oauthData, setOauthData] = useState<{
    authorize_url: string;
    is_oauth_configured: boolean;
    client_id_configured: boolean;
  } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const activePid = getActiveProjectId();
    fetch(apiUrl(`/api/auth/github/url?project_id=${activePid}`))
      .then((r) => r.ok && r.json())
      .then((data) => {
        setOauthData(data);
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleAuthenticate = async (payload: {
    code?: string;
    token?: string;
    demo_login?: boolean;
    demo_username?: string;
  }) => {
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    const activePid = getActiveProjectId();

    try {
      const resp = await fetch(apiUrl('/api/auth/github/authenticate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          project_id: activePid,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Authentication failed (HTTP ${resp.status})`);
      }

      const data = await resp.json();
      setUserLoginToken(data.login_token, data.user);
      setSuccessMessage(`Authenticated as @${data.user.username}! Profile session saved.`);
      if (onAuthSuccess) onAuthSuccess(data.user);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthRedirect = () => {
    if (oauthData && oauthData.is_oauth_configured && oauthData.authorize_url) {
      window.location.href = oauthData.authorize_url;
    } else {
      // If OAuth App client ID is not configured in .env, seamlessly guide user or offer 1-click test login
      setErrorMessage(
        'GitHub OAuth Client ID is not configured yet in .env (GITHUB_CLIENT_ID). You can either add your GitHub OAuth App credentials or sign in instantly with Demo / PAT.'
      );
    }
  };

  const handleLogout = () => {
    clearUserLoginToken();
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 520,
          backgroundColor: '#0a101d',
          border: '1px solid #1e293b',
          borderRadius: 16,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#0c1322',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                backgroundColor: '#24292f',
                border: '1px solid #334155',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
            </div>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Sign In with GitHub
              </h2>
              <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>
                Authorize with your GitHub account to access your repositories
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 6,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Current User Card (if authenticated) */}
        {currentUser && (
          <div
            style={{
              padding: '16px 24px',
              backgroundColor: 'rgba(34, 197, 94, 0.05)',
              borderBottom: '1px solid rgba(34, 197, 94, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {currentUser.avatar_url && (
                <img
                  src={currentUser.avatar_url}
                  alt={currentUser.username}
                  style={{ width: 36, height: 36, borderRadius: '50%', border: '1.5px solid #4ade80' }}
                />
              )}
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                  {currentUser.name || currentUser.username}
                </div>
                <div style={{ fontSize: 11, color: '#4ade80' }}>@{currentUser.username} (Signed In)</div>
              </div>
            </div>

            <button
              onClick={handleLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 12px',
                borderRadius: 6,
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <LogOut size={13} />
              <span>Sign Out</span>
            </button>
          </div>
        )}

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #1e293b',
            backgroundColor: '#090e1a',
            padding: '0 24px',
          }}
        >
          <button
            onClick={() => setTab('oauth')}
            style={{
              padding: '12px 16px',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'oauth' ? '2px solid #38bdf8' : '2px solid transparent',
              color: tab === 'oauth' ? '#38bdf8' : '#94a3b8',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            GitHub OAuth Login
          </button>
          <button
            onClick={() => setTab('demo')}
            style={{
              padding: '12px 16px',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'demo' ? '2px solid #38bdf8' : '2px solid transparent',
              color: tab === 'demo' ? '#38bdf8' : '#94a3b8',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Instant Demo Login
          </button>
          <button
            onClick={() => setTab('pat')}
            style={{
              padding: '12px 16px',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'pat' ? '2px solid #38bdf8' : '2px solid transparent',
              color: tab === 'pat' ? '#38bdf8' : '#94a3b8',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Access Token (PAT)
          </button>
        </div>

        {/* Tab Body */}
        <div style={{ padding: 24 }}>
          {errorMessage && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 8,
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#f87171',
                fontSize: 12,
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <AlertCircle size={15} />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 8,
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.25)',
                color: '#4ade80',
                fontSize: 12,
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <ShieldCheck size={15} />
              <span>{successMessage}</span>
            </div>
          )}

          {/* TAB 1: Real OAuth (Log in with GitHub Popup / Redirect) */}
          {tab === 'oauth' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20, textAlign: 'center', padding: '10px 0' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                <p style={{ fontSize: 14, color: '#cbd5e1', margin: 0, lineHeight: 1.5 }}>
                  Click below to sign in directly via <strong>GitHub.com</strong>. You will enter your GitHub credentials on GitHub's secure login page and authorize AEGIS.
                </p>
                <span style={{ fontSize: 12, color: '#64748b' }}>
                  No password or secrets are ever handled or stored by this app.
                </span>
              </div>

              <button
                onClick={handleOAuthRedirect}
                disabled={isLoading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 12,
                  padding: '14px 24px',
                  borderRadius: 10,
                  backgroundColor: '#24292f',
                  border: '1.5px solid #334155',
                  color: '#ffffff',
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease, transform 0.15s ease',
                  boxShadow: '0 4px 14px rgba(0, 0, 0, 0.4)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#2f363d';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#24292f';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                  />
                </svg>
                <span>Continue with GitHub</span>
                <ChevronRight size={16} />
              </button>

              <div style={{ fontSize: 12, color: '#64748b' }}>
                Redirects to <code>github.com/login/oauth/authorize</code> with <code>repo, read:org</code> scopes.
              </div>
            </div>
          )}

          {/* TAB 2: Instant Demo / One-Click Login */}
          {tab === 'demo' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <p style={{ fontSize: 13, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                Test the app instantly without setting up GitHub OAuth or entering tokens. It verifies instantly and saves your session.
              </p>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                  GitHub Username Handle
                </label>
                <input
                  type="text"
                  value={demoUsername}
                  onChange={(e) => setDemoUsername(e.target.value)}
                  placeholder="e.g. muneeb-sawez"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#030712',
                    border: '1px solid #1e293b',
                    borderRadius: 8,
                    color: '#f8fafc',
                    fontSize: 13,
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <button
                  disabled={isLoading}
                  onClick={() => handleAuthenticate({ demo_login: true, demo_username: demoUsername.trim() })}
                  style={{
                    padding: '8px 18px',
                    backgroundColor: '#10b981',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {isLoading ? 'Signing in...' : 'Sign In Instantly'}
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: Personal Access Token (Fallback option) */}
          {tab === 'pat' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <p style={{ fontSize: 13, color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                If you prefer not using OAuth redirect, you can enter a Personal Access Token with <code>repo</code> permissions.
              </p>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                  GitHub Personal Access Token (ghp_... or github_pat_...)
                </label>
                <input
                  type="password"
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  value={patToken}
                  onChange={(e) => setPatToken(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#030712',
                    border: '1px solid #1e293b',
                    borderRadius: 8,
                    color: '#f8fafc',
                    fontSize: 13,
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,read:org,user:email&description=AEGIS+Reliability+Platform"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: 12,
                    color: '#38bdf8',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  <span>Generate token on GitHub</span>
                  <ExternalLink size={12} />
                </a>

                <button
                  disabled={isLoading || !patToken.trim()}
                  onClick={() => handleAuthenticate({ token: patToken.trim() })}
                  style={{
                    padding: '8px 18px',
                    backgroundColor: patToken.trim() ? '#0284c7' : '#1e293b',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: patToken.trim() ? 'pointer' : 'not-allowed',
                  }}
                >
                  {isLoading ? 'Verifying...' : 'Sign In with Token'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
