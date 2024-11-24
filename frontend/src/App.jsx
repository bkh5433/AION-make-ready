// src/App.jsx
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';

function App() {
  return (
      <ThemeProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-[#1a1b1e]">
          <header className="bg-white dark:bg-[#1f2937] border-b border-gray-200 dark:border-gray-800">
            <div className="container mx-auto py-4 px-8 max-w-7xl flex items-center">
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
            </div>
          </header>
          <main className="py-6">
            <PropertyReportGenerator/>
          </main>
          <ThemeToggle/>
        </div>
      </ThemeProvider>
  );
}

export default App;