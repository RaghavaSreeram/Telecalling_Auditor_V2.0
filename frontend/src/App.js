import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { AuthProvider, useAuth } from "./context/AuthContext";
import suppressResizeObserverWarnings from "./utils/suppressWarnings";

// Suppress benign browser warnings
suppressResizeObserverWarnings();
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Scripts from "./pages/Scripts";
import UploadAudio from "./pages/UploadAudio";
import AuditResults from "./pages/AuditResults";
import AuditDetail from "./pages/AuditDetail";
import ManagerDashboard from "./pages/ManagerDashboard";
import AuditorDashboard from "./pages/AuditorDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import Layout from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Toaster } from "./components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Axios interceptor for auth
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Role-based redirect component
const RoleBasedRedirect = () => {
  const { user } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  // Redirect based on role
  if (user.role === 'admin') {
    return <Navigate to="/admin" replace />;
  } else if (user.role === 'manager') {
    return <Navigate to="/manager" replace />;
  } else if (user.role === 'auditor') {
    return <Navigate to="/auditor" replace />;
  }
  
  return <Navigate to="/login" replace />;
};

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={!user ? <Login /> : <RoleBasedRedirect />}
        />
        
        <Route
          path="/"
          element={
            user ? <Layout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<RoleBasedRedirect />} />
          
          {/* Admin Routes */}
          <Route
            path="admin"
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Manager Routes - Admin also has access */}
          <Route
            path="manager"
            element={
              <ProtectedRoute allowedRoles={['manager', 'admin']}>
                <ManagerDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Auditor Routes */}
          <Route
            path="auditor"
            element={
              <ProtectedRoute requiredRole="auditor">
                <AuditorDashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Shared Routes (Both roles) */}
          <Route path="scripts" element={<Scripts />} />
          <Route path="upload" element={<UploadAudio />} />
          <Route path="audits" element={<AuditResults />} />
          <Route path="audits/:auditId" element={<AuditDetail />} />
          
          {/* Legacy dashboard route */}
          <Route path="dashboard" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <AppRoutes />
        <Toaster position="top-right" />
      </div>
    </AuthProvider>
  );
}

export default App;
