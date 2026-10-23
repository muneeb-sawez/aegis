import { useState, useEffect } from 'react';
import {
  X,
  Search,
  FolderGit2,
  GitBranch,
  Check,
  RefreshCw,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import {
  apiUrl,
  getAuthHeaders,
  getActiveProjectId,
  setActiveProjectId,
} from '../config';
import type { GitHubRepoSummary } from '../config';

interface GitHubRepoSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRepoSelected?: (repo: GitHubRepoSummary) => void;
  onOpenAuthModal?: () => void;
}

export function GitHubRepoSelectorModal({
  isOpen,
  onClose,
  onRepoSelected,
}: GitHubRepoSelectorModalProps) {
  const [repos, setRepos] = useState<GitHubRepoSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepoSummary | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [customGitUrl, setCustomGitUrl] = useState<string>('');
  const [tab, setTab] = useState<'my_repos' | 'custom_url'>('my_repos');

  const activePid = getActiveProjectId();

  useEffect(() => {
    if (!isOpen) return;
    loadRepos();
  }, [isOpen]);

  const loadRepos = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resp = await fetch(apiUrl('/api/auth/github/repos'), {
        headers: getAuthHeaders(activePid),
      });
      if (resp.ok) {
        const data: GitHubRepoSummary[] = await resp.json();
        setRepos(data);
      } else {
        const err = await resp.json().catch(() => ({}));
        setErrorMessage(err.detail || 'Could not load GitHub repositories.');
      }
    } catch (e: any) {
      setErrorMessage(e.message || 'Error fetching repositories.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredRepos = repos.filter((r) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      r.name.toLowerCase().includes(q) ||
      r.full_name.toLowerCase().includes(q) ||
      (r.description && r.description.toLowerCase().includes(q))
    );
  });

  const handleImportSelectedRepo = async () => {
    if (!selectedRepo) return;
    setIsImporting(true);
    setErrorMessage(null);
    setImportStatus(`Cloning & parsing AST for ${selectedRepo.full_name}...`);

    try {
      const resp = await fetch(apiUrl(`/api/projects/${activePid}/import-github`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(activePid),
        },
        body: JSON.stringify({
          repo_full_name: selectedRepo.full_name,
          branch: selectedBranch || selectedRepo.default_branch || 'main',
          mode: 'replace',
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to import repo (HTTP ${resp.status})`);
      }

      const result = await resp.json();
      setImportStatus(`Success! Imported ${result.node_count || 0} nodes.`);
      if (onRepoSelected) onRepoSelected(selectedRepo);

      setTimeout(() => {
        onClose();
        window.location.hash = 'topology';
      }, 1000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to import repository.');
      setImportStatus(null);
    } finally {
      setIsImporting(false);
    }
  };

  const handleImportCustomUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customGitUrl.trim()) return;

    setIsImporting(true);
    setErrorMessage(null);
    setImportStatus(`Cloning and analyzing repository from ${customGitUrl}...`);

    try {
      const resp = await fetch(apiUrl('/api/projects/integrate-github'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(activePid),
        },
        body: JSON.stringify({
          repo_url: customGitUrl.trim(),
          branch: selectedBranch || 'main',
          mode: 'replace',
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to integrate repo (HTTP ${resp.status})`);
      }

      const data = await resp.json();
      const newPid = data.project_id || activePid;
      setActiveProjectId(newPid);
      setImportStatus(`Import complete for ${data.repo_full_name || 'repository'}!`);

      setTimeout(() => {
        onClose();
        window.location.hash = 'topology';
      }, 1000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to import repository.');
      setImportStatus(null);
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.8)',
        backdropFilter: 'blur(6px)',
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
          maxWidth: 680,
          maxHeight: '85vh',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <FolderGit2 size={16} />
            </div>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Select GitHub Repository
              </h2>
              <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>
                Choose any repo from your account to generate topology & run risk simulations
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

        {/* Tab switch */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #1e293b',
            backgroundColor: '#090e1a',
            padding: '0 24px',
          }}
        >
          <button
            onClick={() => setTab('my_repos')}
            style={{
              padding: '12px 16px',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'my_repos' ? '2px solid #38bdf8' : '2px solid transparent',
              color: tab === 'my_repos' ? '#38bdf8' : '#94a3b8',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            My Repositories ({repos.length})
          </button>
          <button
            onClick={() => setTab('custom_url')}
            style={{
              padding: '12px 16px',
              background: 'none',
              border: 'none',
              borderBottom: tab === 'custom_url' ? '2px solid #38bdf8' : '2px solid transparent',
              color: tab === 'custom_url' ? '#38bdf8' : '#94a3b8',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Public Git URL
          </button>
        </div>

        {/* Notices */}
        {errorMessage && (
          <div
            style={{
              margin: '16px 24px 0 24px',
              padding: '10px 14px',
              borderRadius: 8,
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              color: '#f87171',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <AlertCircle size={15} />
            <span>{errorMessage}</span>
          </div>
        )}

        {importStatus && (
          <div
            style={{
              margin: '16px 24px 0 24px',
              padding: '10px 14px',
              borderRadius: 8,
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              color: '#38bdf8',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Sparkles size={15} />
            <span>{importStatus}</span>
          </div>
        )}

        {/* Content Body */}
        {tab === 'my_repos' ? (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            {/* Search and refresh toolbar */}
            <div style={{ padding: '16px 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: '#030712',
                  border: '1px solid #1e293b',
                  borderRadius: 8,
                  padding: '8px 12px',
                  gap: 8,
                }}
              >
                <Search size={15} color="#64748b" />
                <input
                  type="text"
                  placeholder="Filter repositories by name or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    color: '#f8fafc',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <button
                onClick={loadRepos}
                disabled={isLoading}
                title="Refresh repositories"
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: 8,
                  color: '#94a3b8',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 12,
                }}
              >
                <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Repos list */}
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '0 24px 16px 24px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b', fontSize: 13 }}>
                  Fetching repositories from GitHub...
                </div>
              ) : filteredRepos.length > 0 ? (
                filteredRepos.map((repo) => {
                  const isSelected = selectedRepo?.id === repo.id;
                  return (
                    <div
                      key={repo.id}
                      onClick={() => {
                        setSelectedRepo(repo);
                        setSelectedBranch(repo.default_branch || 'main');
                      }}
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : '#0d1526',
                        border: isSelected ? '1.5px solid #38bdf8' : '1px solid #1e293b',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        transition: 'border-color 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                            {repo.full_name}
                          </span>
                          <span
                            style={{
                              fontSize: 10,
                              padding: '1px 6px',
                              borderRadius: 4,
                              backgroundColor: repo.private ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                              color: repo.private ? '#f87171' : '#34d399',
                              border: `1px solid ${repo.private ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`,
                            }}
                          >
                            {repo.private ? 'Private' : 'Public'}
                          </span>
                        </div>
                        {repo.description && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#94a3b8',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {repo.description}
                          </div>
                        )}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, color: '#64748b' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <GitBranch size={11} /> {repo.default_branch || 'main'}
                          </span>
                        </div>
                      </div>

                      <div style={{ marginLeft: 16 }}>
                        {isSelected ? (
                          <div
                            style={{
                              width: 24,
                              height: 24,
                              borderRadius: '50%',
                              backgroundColor: '#38bdf8',
                              color: '#030712',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            <Check size={14} />
                          </div>
                        ) : (
                          <div
                            style={{
                              width: 24,
                              height: 24,
                              borderRadius: '50%',
                              border: '1.5px solid #334155',
                            }}
                          />
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b', fontSize: 13 }}>
                  No matching repositories found.
                </div>
              )}
            </div>

            {/* Selected Repo Footer Actions */}
            <div
              style={{
                padding: '16px 24px',
                borderTop: '1px solid #1e293b',
                backgroundColor: '#0c1322',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              {selectedRepo ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>Branch to import:</span>
                  <input
                    type="text"
                    value={selectedBranch}
                    onChange={(e) => setSelectedBranch(e.target.value)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: 4,
                      backgroundColor: '#030712',
                      border: '1px solid #1e293b',
                      color: '#f8fafc',
                      fontSize: 12,
                      width: 100,
                    }}
                  />
                </div>
              ) : (
                <span style={{ fontSize: 12, color: '#64748b' }}>Select a repository above to import</span>
              )}

              <button
                disabled={!selectedRepo || isImporting}
                onClick={handleImportSelectedRepo}
                style={{
                  padding: '9px 20px',
                  borderRadius: 8,
                  backgroundColor: selectedRepo && !isImporting ? '#0284c7' : '#1e293b',
                  color: '#ffffff',
                  fontSize: 13,
                  fontWeight: 600,
                  border: 'none',
                  cursor: selectedRepo && !isImporting ? 'pointer' : 'not-allowed',
                }}
              >
                {isImporting ? 'Importing...' : 'Ingest & Scan Repository'}
              </button>
            </div>
          </div>
        ) : (
          /* Custom Git URL tab */
          <form onSubmit={handleImportCustomUrl} style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <p style={{ fontSize: 13, color: '#94a3b8', margin: 0 }}>
              Directly integrate any public GitHub repository (e.g., Spring PetClinic, Google Microservices Demo, or your own public repo).
            </p>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#cbd5e1', marginBottom: 6 }}>
                Repository Git URL
              </label>
              <input
                type="text"
                placeholder="https://github.com/spring-petclinic/spring-petclinic-microservices"
                value={customGitUrl}
                onChange={(e) => setCustomGitUrl(e.target.value)}
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

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
              <button
                type="submit"
                disabled={!customGitUrl.trim() || isImporting}
                style={{
                  padding: '9px 20px',
                  borderRadius: 8,
                  backgroundColor: customGitUrl.trim() && !isImporting ? '#0284c7' : '#1e293b',
                  color: '#ffffff',
                  fontSize: 13,
                  fontWeight: 600,
                  border: 'none',
                  cursor: customGitUrl.trim() && !isImporting ? 'pointer' : 'not-allowed',
                }}
              >
                {isImporting ? 'Importing...' : 'Scan & Ingest URL'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
