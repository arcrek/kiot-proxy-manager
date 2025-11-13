import React, { useState, useEffect } from 'react';
import './App.css';
import { Proxy, Settings, AddProxyRequest, RotateProxyRequest, UpdateSettingsRequest } from './types';
import * as api from './api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState<'proxies' | 'settings'>('proxies');
  
  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        await api.getCurrentUser();
        setIsAuthenticated(true);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
      setIsAuthenticated(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="dashboard">
      <nav className="navbar">
        <div className="navbar-brand">KiotProxy Manager</div>
        <ul className="nav-menu">
          <li 
            className={`nav-item ${currentPage === 'proxies' ? 'active' : ''}`}
            onClick={() => setCurrentPage('proxies')}
          >
            📡 Proxies
          </li>
          <li 
            className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
            onClick={() => setCurrentPage('settings')}
          >
            ⚙️ Settings
          </li>
          <li className="nav-item logout" onClick={handleLogout}>
            🚪 Logout
          </li>
        </ul>
      </nav>
      <main className="main-content">
        {currentPage === 'proxies' && <ProxiesPage />}
        {currentPage === 'settings' && <SettingsPage />}
      </main>
    </div>
  );
}

// Login Page Component
function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.login(username, password);
      onLogin();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>KiotProxy Manager</h1>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}

// Proxies Page Component
function ProxiesPage() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkImportModal, setShowBulkImportModal] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadProxies = async () => {
    try {
      const data = await api.getProxies();
      setProxies(data);
    } catch (error) {
      console.error('Failed to load proxies:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProxies();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadProxies, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRotate = async (id: number, region: string) => {
    try {
      await api.rotateProxy(id, { region });
      showToast('Proxy rotated successfully', 'success');
      loadProxies();
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to rotate proxy', 'error');
    }
  };

  const handleUpdate = async (id: number) => {
    try {
      await api.updateProxy(id);
      showToast('Proxy updated successfully', 'success');
      loadProxies();
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to update proxy', 'error');
    }
  };

  const handleCheckProxy = async (id: number) => {
    try {
      await api.checkProxy(id);
      showToast('Proxy check started', 'success');
      // Reload after a short delay to see updated status
      setTimeout(() => loadProxies(), 2000);
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to check proxy', 'error');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this proxy?')) return;
    
    try {
      await api.deleteProxy(id);
      showToast('Proxy deleted successfully', 'success');
      loadProxies();
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to delete proxy', 'error');
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const copyToClipboard = async (text: string, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
      e.preventDefault();
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied to clipboard!', 'success');
    } catch (error) {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        showToast('Copied to clipboard!', 'success');
      } catch (err) {
        showToast('Failed to copy', 'error');
      }
      document.body.removeChild(textArea);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading proxies...</div>;
  }

  return (
    <>
      <div className="page-header">
        <h1>Proxy Management</h1>
        <p>Manage your KiotProxy instances</p>
      </div>

      <div className="actions-bar">
        <button className="btn-primary" onClick={() => setShowAddModal(true)}>
          ➕ Add Proxy
        </button>
        <button className="btn-primary" onClick={() => setShowBulkImportModal(true)}>
          📥 Bulk Import
        </button>
        <button className="btn-secondary" onClick={loadProxies}>
          🔄 Refresh
        </button>
      </div>

      <div className="proxy-table">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Key</th>
              <th>KP Proxy</th>
              <th>IP</th>
              <th>Public Endpoint</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {proxies.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px' }}>
                  No proxies yet. Click "Add Proxy" to get started.
                </td>
              </tr>
            ) : (
              proxies.map((proxy, index) => (
                <tr key={proxy.id}>
                  <td>{index + 1}</td>
                  <td>
                    <div>{proxy.key_name}</div>
                  </td>
                  <td>
                    <div className="proxy-info">
                      {proxy.remote_http && (
                        <>
                          <div>
                            <span className="proxy-info-label">HTTP:</span>{' '}
                            <span className="proxy-info-value">{proxy.remote_http}</span>
                          </div>
                        </>
                      )}
                    </div>
                  </td>
                  <td>
                    {proxy.remote_ip && (
                      <div>
                        {proxy.remote_ip}
                        {proxy.location && (
                          <span className="location-badge">{proxy.location}</span>
                        )}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="proxy-info">
                      <span className="proxy-info-value">{proxy.endpoint}</span>
                      <button
                        className="copy-btn"
                        onClick={(e) => copyToClipboard(proxy.endpoint, e)}
                        title="Copy endpoint"
                      >
                        📋 Copy
                      </button>
                    </div>
                  </td>
                  <td>
                    <span className={`status-badge status-${proxy.status}`}>
                      {proxy.status === 'active' ? '✅' : '❌'}{' '}
                      {proxy.latency_ms !== undefined ? `${proxy.latency_ms}ms` : '0ms'}
                    </span>
                  </td>
                  <td>
                    <div className="actions-cell">
                      <button
                        className="btn-icon"
                        onClick={() => handleRotate(proxy.id, 'random')}
                        title="Rotate to new IP"
                      >
                        🔄
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleUpdate(proxy.id)}
                        title="Update proxy info"
                      >
                        ↻
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleCheckProxy(proxy.id)}
                        title="Check proxy health"
                      >
                        🔍
                      </button>
                      <button
                        className="btn-icon delete"
                        onClick={() => handleDelete(proxy.id)}
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAddModal && (
        <AddProxyModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            loadProxies();
            showToast('Proxy added successfully', 'success');
          }}
          onError={(message) => showToast(message, 'error')}
        />
      )}

      {showBulkImportModal && (
        <BulkImportModal
          onClose={() => setShowBulkImportModal(false)}
          onSuccess={(count) => {
            setShowBulkImportModal(false);
            loadProxies();
            showToast(`Successfully imported ${count} proxies!`, 'success');
          }}
          onError={(message) => showToast(message, 'error')}
        />
      )}

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </>
  );
}

// Add Proxy Modal Component
function AddProxyModal({
  onClose,
  onSuccess,
  onError,
}: {
  onClose: () => void;
  onSuccess: () => void;
  onError: (message: string) => void;
}) {
  const [formData, setFormData] = useState<AddProxyRequest>({
    kiotproxy_key: '',
    region: 'random',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await api.createProxy(formData);
      onSuccess();
    } catch (error: any) {
      onError(error.response?.data?.detail || 'Failed to create proxy');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Add New Proxy</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>KiotProxy API Key</label>
            <input
              type="text"
              value={formData.kiotproxy_key}
              onChange={(e) => setFormData({ ...formData, kiotproxy_key: e.target.value })}
              placeholder="K6fa3db6..."
              required
            />
            <small style={{ color: '#888' }}>
              Name will be auto-generated from proxy location
            </small>
          </div>
          <div className="form-group">
            <label>Region</label>
            <select
              value={formData.region}
              onChange={(e) => setFormData({ ...formData, region: e.target.value })}
            >
              <option value="random">Random</option>
              <option value="bac">Bắc (North)</option>
              <option value="trung">Trung (Central)</option>
              <option value="nam">Nam (South)</option>
            </select>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Adding...' : 'Add Proxy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Bulk Import Modal Component
function BulkImportModal({
  onClose,
  onSuccess,
  onError,
}: {
  onClose: () => void;
  onSuccess: (count: number) => void;
  onError: (message: string) => void;
}) {
  const [formData, setFormData] = useState({
    kiotproxy_keys: '',
    region: 'random',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResults(null);

    try {
      const response = await api.bulkImportProxies(formData);
      setResults(response);
      
      if (response.failed_count === 0) {
        // All succeeded, close and show success
        setTimeout(() => onSuccess(response.success_count), 1500);
      }
    } catch (error: any) {
      onError(error.response?.data?.detail || 'Failed to import proxies');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
        <h2>📥 Bulk Import Proxies</h2>
        
        {!results ? (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>KiotProxy API Keys (one per line)</label>
              <textarea
                value={formData.kiotproxy_keys}
                onChange={(e) => setFormData({ ...formData, kiotproxy_keys: e.target.value })}
                placeholder="K6fa3db6...&#10;K7ab2cd8...&#10;K8bc3de9..."
                rows={10}
                style={{ fontFamily: 'monospace', fontSize: '14px' }}
                required
              />
              <small style={{ color: '#888' }}>
                Enter up to 50 keys. Names will be auto-generated from location.
              </small>
            </div>
            <div className="form-group">
              <label>Default Region (for rotation)</label>
              <select
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
              >
                <option value="random">Random</option>
                <option value="bac">Bắc (North)</option>
                <option value="trung">Trung (Central)</option>
                <option value="nam">Nam (South)</option>
              </select>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-cancel" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={isLoading}>
                {isLoading ? 'Importing...' : 'Import All'}
              </button>
            </div>
          </form>
        ) : (
          <div>
            <div style={{ marginBottom: '20px' }}>
              <h3>Import Results</h3>
              <p>
                Total: {results.total} | 
                ✅ Success: {results.success_count} | 
                ❌ Failed: {results.failed_count}
              </p>
            </div>

            {results.results.success.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: '#10b981' }}>✅ Successfully Imported</h4>
                <div style={{ maxHeight: '200px', overflow: 'auto', fontSize: '13px' }}>
                  {results.results.success.map((item: any, idx: number) => (
                    <div key={idx} style={{ padding: '5px', borderBottom: '1px solid #eee' }}>
                      <strong>{item.name}</strong> - {item.ip} → {item.subdomain}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.results.failed.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: '#ef4444' }}>❌ Failed Imports</h4>
                <div style={{ maxHeight: '200px', overflow: 'auto', fontSize: '13px' }}>
                  {results.results.failed.map((item: any, idx: number) => (
                    <div key={idx} style={{ padding: '5px', borderBottom: '1px solid #eee' }}>
                      <strong>{item.key}</strong> - {item.error}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button 
                className="btn-primary" 
                onClick={() => results.failed_count === 0 ? onSuccess(results.success_count) : onClose()}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Settings Page Component
function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;

    setIsSaving(true);
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      showToast('Settings saved successfully', 'success');
    } catch (error: any) {
      showToast(error.response?.data?.detail || 'Failed to save settings', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  if (isLoading || !settings) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Configure auto-rotation settings</p>
      </div>

      <div className="settings-card">
        <h2>Auto-Rotation Settings</h2>
        
        <div className="setting-item">
          <div className="setting-header">
            <input
              type="checkbox"
              id="rotate-expiration"
              checked={settings.auto_rotate_on_expiration}
              onChange={(e) =>
                setSettings({ ...settings, auto_rotate_on_expiration: e.target.checked })
              }
            />
            <label htmlFor="rotate-expiration">Auto-rotate on expiration</label>
          </div>
          <p className="setting-description">
            Automatically rotate proxies after 30 minutes (when KiotProxy proxy expires)
          </p>
        </div>

        <div className="setting-item">
          <div className="setting-header">
            <input
              type="checkbox"
              id="rotate-interval"
              checked={settings.auto_rotate_interval_enabled}
              onChange={(e) =>
                setSettings({ ...settings, auto_rotate_interval_enabled: e.target.checked })
              }
            />
            <label htmlFor="rotate-interval">Timed auto-rotation</label>
          </div>
          <p className="setting-description">
            Rotate all proxies at regular intervals
          </p>
          {settings.auto_rotate_interval_enabled && (
            <div className="setting-input">
              <label>Interval (minutes, min: 2):</label>
              <input
                type="number"
                min="2"
                value={settings.auto_rotate_interval_minutes}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    auto_rotate_interval_minutes: parseInt(e.target.value) || 2,
                  })
                }
              />
            </div>
          )}
        </div>

        <button className="btn-primary" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </>
  );
}

export default App;

