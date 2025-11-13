export interface Proxy {
  id: number;
  key_name: string;
  subdomain: string;
  endpoint: string;
  remote_http?: string;
  remote_ip?: string;
  location?: string;
  status: string;
  latency_ms?: number;
  expiration_at?: string;
  ttl?: number;
  ttc?: number;
  last_check_at?: string;
  last_rotated_at?: string;
  created_at: string;
}

export interface Settings {
  auto_rotate_on_expiration: boolean;
  auto_rotate_interval_enabled: boolean;
  auto_rotate_interval_minutes: number;
}

export interface AddProxyRequest {
  kiotproxy_key: string;
  region: string;
}

export interface BulkImportRequest {
  kiotproxy_keys: string;  // Newline-separated keys
  region: string;
}

export interface BulkImportResponse {
  total: number;
  success_count: number;
  failed_count: number;
  results: {
    success: Array<{
      key: string;
      name: string;
      subdomain: string;
      ip: string;
    }>;
    failed: Array<{
      key: string;
      error: string;
    }>;
  };
}

export interface RotateProxyRequest {
  region: string;
}

export interface UpdateSettingsRequest {
  auto_rotate_on_expiration?: boolean;
  auto_rotate_interval_enabled?: boolean;
  auto_rotate_interval_minutes?: number;
}

export interface User {
  username: string;
}

