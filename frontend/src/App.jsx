// src/App.jsx
import {BrowserRouter, Routes, Route, Navigate, useNavigate} from 'react-router-dom';
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';
import LoginPage from './components/auth/LoginPage';
import {LogOut, Settings} from 'lucide-react';
import {AuthProvider, useAuth} from './lib/auth';
import AdminDashboard from './components/admin/AdminDashboard';

// Protected Route component
const ProtectedRoute = ({children}) => {
  const authToken = localStorage.getItem('authToken');

  if (!authToken) {
    return <Navigate to="/login" replace/>;
  }

  return children;
};

// Create a separate component for the authenticated layout
const AuthenticatedLayout = () => {
  const {user} = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    localStorage.removeItem('authToken');
    window.location.href = '/login';
  };

  const handleAdminClick = () => {
    navigate('/admin');
  };

  return (
      <div>
        <header className="bg-white dark:bg-[#1f2937] border-b border-gray-200 dark:border-gray-800">
          <div className="container mx-auto py-4 px-8 max-w-7xl flex items-center justify-between">
            {/* Logo and Company Name */}
            <div className="flex items-center gap-3">
              <img
                  src="/aion-logo.png"
                  alt="AION Logo"
                  className="w-8 h-8 object-contain"
              />
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Break Even Report Generator
              </h1>
            </div>

            {/* Right side controls */}
            <div className="flex items-center gap-4">
              <ThemeToggle/>
              {user?.role === 'admin' && (
                  <button
                      onClick={handleAdminClick}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg
                  text-gray-700 dark:text-gray-200 
                  hover:bg-gray-100 dark:hover:bg-gray-800
                  transition-colors duration-200"
                  >
                    <Settings className="h-5 w-5"/>
                    <span className="hidden sm:inline">Admin Dashboard</span>
                  </button>
              )}
              <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg
                text-gray-700 dark:text-gray-200 
                hover:bg-gray-100 dark:hover:bg-gray-800
                transition-colors duration-200"
              >
                <LogOut className="h-5 w-5"/>
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>
        <main className="pt-8">
          <PropertyReportGenerator/>
        </main>
      </div>
  );
};

function App() {
  return (
      <AuthProvider>
        <BrowserRouter>
          <ThemeProvider>
            <div className="min-h-screen bg-gray-50 dark:bg-[#1a1b1e]">
              <Routes>
                <Route path="/login" element={<LoginPage/>}/>
                <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <AuthenticatedLayout/>
                      </ProtectedRoute>
                    }
                />
                <Route
                    path="/admin"
                    element={
                      <ProtectedRoute>
                        <AdminDashboard/>
                      </ProtectedRoute>
                    }
              />
            </Routes>
          </div>
        </ThemeProvider>
      </BrowserRouter>
      </AuthProvider>
  );
}

export default App;