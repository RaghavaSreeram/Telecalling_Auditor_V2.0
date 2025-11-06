import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
        
        // Fetch user permissions
        const response = await axios.get(`${API}/rbac/permissions`);
        setPermissions(response.data.permissions);
      } catch (error) {
        console.error('Auth check failed', error);
        logout();
      }
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    
    // Fetch permissions
    const permResponse = await axios.get(`${API}/rbac/permissions`);
    setPermissions(permResponse.data.permissions);
    
    return userData;
  };

  const register = async (email, password, full_name, role = 'auditor') => {
    const response = await axios.post(`${API}/auth/register`, {
      email,
      password,
      full_name,
      role
    });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    
    // Fetch permissions
    const permResponse = await axios.get(`${API}/rbac/permissions`);
    setPermissions(permResponse.data.permissions);
    
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setPermissions([]);
  };

  const hasRole = (role) => {
    return user?.role === role;
  };

  const hasPermission = (permission) => {
    return permissions.includes(permission);
  };

  const isManager = () => {
    return user?.role === 'manager' || user?.role === 'admin';
  };

  const isAuditor = () => {
    return user?.role === 'auditor';
  };

  const value = {
    user,
    permissions,
    loading,
    login,
    register,
    logout,
    hasRole,
    hasPermission,
    isManager,
    isAuditor,
    checkAuth
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
