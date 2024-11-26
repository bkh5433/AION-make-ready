// src/App.jsx
import {BrowserRouter, Routes, Route, Navigate} from 'react-router-dom';
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';
import LoginPage from './components/auth/LoginPage';
import {LogOut} from 'lucide-react'; // Import LogOut icon
import {AuthProvider} from './lib/auth';

// Protected Route component
const ProtectedRoute = ({children}) => {
  const authToken = localStorage.getItem('authToken');

  if (!authToken) {
    return <Navigate to="/login" replace/>;
  }

  return children;
};

function App() {
  const handleLogout = () => {
    localStorage.removeItem('authToken'); // Remove the auth token
    window.location.href = '/login'; // Redirect to login page
  };

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
                        <main className="py-6">
                          <PropertyReportGenerator/>
                        </main>
                      </div>
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