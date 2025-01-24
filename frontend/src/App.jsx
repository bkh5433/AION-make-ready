// src/App.jsx
import {BrowserRouter, Routes, Route, Navigate, useNavigate} from 'react-router-dom';
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';
import LoginPage from './components/auth/LoginPage';
import ChangePasswordPage from './components/auth/ChangePasswordPage';
import {LogOut, Settings, AlertTriangle} from 'lucide-react';
import {AuthProvider, useAuth} from './lib/auth';
import AdminDashboard from './components/admin/AdminDashboard';
import MaintenancePage from './components/ui/maintenance-page';
import {useImportWindow} from './lib/hooks/useImportWindow';
import {motion} from 'framer-motion';
import {useState} from 'react';
import MicrosoftCallback from './components/auth/MicrosoftCallback';

// Protected Route component
const ProtectedRoute = ({children}) => {
  const authToken = localStorage.getItem('authToken');

  if (!authToken) {
    return <Navigate to="/login" replace/>;
  }

  return children;
};

const AdminBypassBanner = ({onClose}) => (
    <motion.div
        initial={{opacity: 0, y: -20}}
        animate={{opacity: 1, y: 0}}
        exit={{opacity: 0, y: -20}}
        className="fixed top-0 left-0 right-0 z-[60] bg-yellow-500/10 border-b border-yellow-500/20 backdrop-blur-sm"
    >
        <div className="container mx-auto px-4 py-2 flex items-center justify-between text-yellow-500">
            <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4"/>
                <span className="text-sm">Database update in progress. Admin bypass active.</span>
            </div>
            <button
                onClick={onClose}
                className="text-sm underline underline-offset-4 hover:text-yellow-400"
            >
                Return to maintenance page
            </button>
        </div>
    </motion.div>
);

// Create a separate component for the authenticated layout
const AuthenticatedLayout = () => {
  const {user} = useAuth();
  const navigate = useNavigate();
    const {isInImportWindow, isLoading, checkStatus} = useImportWindow();
    const [bypassMaintenance, setBypassMaintenance] = useState(false);
  
  const handleLogout = () => {
    localStorage.removeItem('authToken');
    window.location.href = '/login';
  };

  const handleAdminClick = () => {
    navigate('/admin');
  };

    // Show maintenance page only if:
    // 1. We're in an import window
    // 2. Not loading
    // 3. User is not an admin OR admin hasn't chosen to bypass
    const showMaintenance = isInImportWindow && !isLoading && (!user?.role === 'admin' || !bypassMaintenance);

  return (
      <>
          {showMaintenance ? (
              <MaintenancePage
                  onCheckStatus={checkStatus}
                  isAdmin={user?.role === 'admin'}
                  onAdminBypass={() => setBypassMaintenance(true)}
              />
          ) : (
              <>
                  {isInImportWindow && bypassMaintenance && (
                      <AdminBypassBanner onClose={() => setBypassMaintenance(false)}/>
                  )}

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
                                  <div className="flex items-center gap-2">
                                      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                                          AION Vista
                                      </h1>
                                      <span className="px-2 py-0.5 text-xs font-medium rounded-full 
                                          bg-blue-100 dark:bg-blue-900/50 
                                          text-blue-600 dark:text-blue-400
                                          border border-blue-200 dark:border-blue-800/50
                                          animate-pulse-subtle">
                                          Preview
                                      </span>
                                  </div>
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
              </>
          )}
      </>
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
                  <Route path="/change-password" element={
                      <ProtectedRoute>
                          <ChangePasswordPage/>
                      </ProtectedRoute>
                  }/>
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
                  <Route path="/auth/callback" element={<MicrosoftCallback/>}/>
              </Routes>
            </div>
          </ThemeProvider>
        </BrowserRouter>
      </AuthProvider>
  );
}

export default App;