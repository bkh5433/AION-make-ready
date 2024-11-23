// src/App.jsx
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';

function App() {
  return (
      <ThemeProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-[#1a1b1e]">
          <header className="bg-black dark:bg-black border-b border-gray-200 dark:border-gray-800 shadow-sm">
            <div className="max-w-4xl mx-auto py-4 px-4 flex items-center">
              {/* Logo and Company Name */}
              <div className="flex items-center gap-3">
                <img
                    src="/aion-logo.png"
                    alt="AION Logo"
                    className="w-8 h-8 object-contain"
                />
                <h1 className="text-2xl font-bold text-white">
                  Break Even Report Generator
              </h1>
            </div>
            </div>
          </header>
          <main className="max-w-4xl mx-auto p-6">
            <PropertyReportGenerator/>
          </main>
          <ThemeToggle/>
        </div>
      </ThemeProvider>
  );
}


export default App;