// src/App.jsx
import {ThemeProvider} from './lib/theme';
import ThemeToggle from './components/ui/theme-toggle';
import PropertyReportGenerator from './components/PropertyReportGenerator';

function App() {
  return (
      <ThemeProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <header className="bg-white dark:bg-gray-800 shadow">
            <div className="max-w-4xl mx-auto py-6 px-4">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Property Report Generator
              </h1>
            </div>
          </header>
          <main>
            <PropertyReportGenerator/>
          </main>
          <ThemeToggle/>
        </div>
      </ThemeProvider>
  );
}

export default App;