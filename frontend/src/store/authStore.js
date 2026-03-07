import { create } from 'zustand';
import { authAPI } from '../services/api';

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  loading: false,
  error: null,

  login: async (email, password, totpToken = null) => {
    set({ loading: true, error: null });
    try {
      const response = await authAPI.login({ email, password, totp_token: totpToken });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      set({ token: access_token, isAuthenticated: true, loading: false });
      return { success: true };
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Login failed';
      set({ error: errorMsg, loading: false });
      return { success: false, error: errorMsg };
    }
  },

  register: async (email, username, password) => {
    set({ loading: true, error: null });
    try {
      await authAPI.register({ email, username, password });
      set({ loading: false });
      return { success: true };
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Registration failed';
      set({ error: errorMsg, loading: false });
      return { success: false, error: errorMsg };
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    try {
      const response = await authAPI.getCurrentUser();
      set({ user: response.data });
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  },
}));
