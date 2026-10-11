import React, { createContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Remove tokens written by older builds; browser sessions now use an
    // HttpOnly cookie that JavaScript cannot read.
    localStorage.removeItem('token');
    api.getMe()
      .then(userData => setUser(userData))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    setUser(data.user);
    return data.user;
  };

  const register = async (username, email, password, termsAccepted, fullName) => {
    return await api.register(username, email, password, termsAccepted, fullName);
  };

  const updateProfile = async (profile) => {
    const updatedUser = await api.updateProfile(profile);
    setUser(updatedUser);
    return updatedUser;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // Clear local UI state even if the server is unavailable.
    } finally {
      localStorage.removeItem('token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, updateProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
