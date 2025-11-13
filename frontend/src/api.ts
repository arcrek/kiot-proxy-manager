import axios from 'axios';
import { Proxy, Settings, AddProxyRequest, BulkImportRequest, BulkImportResponse, RotateProxyRequest, UpdateSettingsRequest, User } from './types';

const API_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth
export const login = async (username: string, password: string) => {
  const response = await api.post('/auth/login', { username, password });
  return response.data;
};

export const logout = async () => {
  const response = await api.post('/auth/logout');
  return response.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Proxies
export const getProxies = async (): Promise<Proxy[]> => {
  const response = await api.get('/proxies');
  return response.data;
};

export const createProxy = async (data: AddProxyRequest): Promise<Proxy> => {
  const response = await api.post('/proxies', data);
  return response.data;
};

export const bulkImportProxies = async (data: BulkImportRequest): Promise<BulkImportResponse> => {
  const response = await api.post('/proxies/bulk-import', data);
  return response.data;
};

export const rotateProxy = async (id: number, data: RotateProxyRequest): Promise<Proxy> => {
  const response = await api.post(`/proxies/${id}/rotate`, data);
  return response.data;
};

export const updateProxy = async (id: number): Promise<Proxy> => {
  const response = await api.post(`/proxies/${id}/update`);
  return response.data;
};

export const checkProxy = async (id: number) => {
  const response = await api.post(`/proxies/${id}/check`);
  return response.data;
};

export const checkAllProxies = async () => {
  const response = await api.post('/proxies/check-all');
  return response.data;
};

export const updateAllProxies = async () => {
  const response = await api.post('/proxies/update-all');
  return response.data;
};

export const deleteProxy = async (id: number) => {
  const response = await api.delete(`/proxies/${id}`);
  return response.data;
};

// Settings
export const getSettings = async (): Promise<Settings> => {
  const response = await api.get('/settings');
  return response.data;
};

export const updateSettings = async (data: UpdateSettingsRequest): Promise<Settings> => {
  const response = await api.put('/settings', data);
  return response.data;
};

// Logs
export const getLogs = async (proxyId?: number, limit: number = 50) => {
  const params = new URLSearchParams();
  if (proxyId) params.append('proxy_id', proxyId.toString());
  params.append('limit', limit.toString());
  
  const response = await api.get(`/logs?${params.toString()}`);
  return response.data;
};

export default api;

