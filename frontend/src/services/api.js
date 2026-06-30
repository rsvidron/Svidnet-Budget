import axios from 'axios';

// Auto-detect API URL based on environment
const getApiBaseUrl = () => {
  // If VITE_API_URL is set, use it
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // In production (Railway), use relative URL
  if (import.meta.env.PROD) {
    return '/api/v1';
  }

  // In development, use localhost
  return 'http://localhost:8000/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getCurrentUser: () => api.get('/auth/me'),
  setupTOTP: () => api.post('/auth/totp/setup'),
  verifyTOTP: (token) => api.post('/auth/totp/verify', null, { params: { token } }),
};

export const transactionsAPI = {
  getAll: (params) => api.get('/transactions/', { params }),
  getMerchants: (params) => api.get('/transactions/merchants', { params }),
  bulkUpdate: (data) => api.post('/transactions/bulk-update', data),
  bulkUpdateByMerchant: (data) => api.post('/transactions/bulk-update-by-merchant', data),
  create: (data) => api.post('/transactions/', data),
  update: (id, data) => api.put(`/transactions/${id}`, data),
  delete: (id) => api.delete(`/transactions/${id}`),
  clear: () => api.delete('/transactions/clear'),
  upload: (file, accountId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (accountId !== undefined && accountId !== null && accountId !== '') {
      formData.append('account_id', accountId);
    }
    return api.post('/transactions/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  export: (params) => api.post('/transactions/export', null, { params }),
};

export const accountsAPI = {
  getAll: () => api.get('/accounts/'),
  create: (data) => api.post('/accounts/', data),
  update: (id, data) => api.put(`/accounts/${id}`, data),
  delete: (id, reassignTo) => {
    const params = {};
    if (reassignTo !== undefined && reassignTo !== null && reassignTo !== '') {
      params.reassign_to = reassignTo;
    }
    return api.delete(`/accounts/${id}`, { params });
  },
};

export const categoriesAPI = {
  getAll: () => api.get('/categories/'),
  create: (data) => api.post('/categories/', data),
  update: (id, data) => api.put(`/categories/${id}`, data),
  delete: (id) => api.delete(`/categories/${id}`),
  merge: (sourceId, targetId) => api.post(`/categories/${sourceId}/merge/${targetId}`),
  addRule: (data) => api.post('/categories/rules', null, { params: data }),
  recategorize: () => api.post('/categories/recategorize'),
};

export const budgetsAPI = {
  getAll: () => api.get('/budgets/'),
  create: (data) => api.post('/budgets/', data),
  update: (id, data) => api.put(`/budgets/${id}`, data),
  delete: (id) => api.delete(`/budgets/${id}`),
};

export const savingsGoalsAPI = {
  getAll: () => api.get('/savings-goals/'),
  create: (data) => api.post('/savings-goals/', data),
  update: (id, data) => api.put(`/savings-goals/${id}`, data),
  delete: (id) => api.delete(`/savings-goals/${id}`),
  contribute: (id, amount) => api.post(`/savings-goals/${id}/contribute`, null, { params: { amount } }),
};

export const analyticsAPI = {
  getSpendingByCategory: (params) => api.get('/analytics/spending-by-category', { params }),
  getMonthlyTrends: (params) => api.get('/analytics/monthly-trends', { params }),
  getBudgetProgress: (params) => api.get('/analytics/budget-progress', { params }),
  getTopMerchants: (params) => api.get('/analytics/top-merchants', { params }),
  getRecurringTransactions: () => api.get('/analytics/recurring-transactions'),
  getDashboard: (params) => api.get('/analytics/dashboard', { params }),
};

export default api;
