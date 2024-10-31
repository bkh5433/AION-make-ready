import PropertyReportGenerator from './components/PropertyReportGenerator'

function App() {
    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow">
                <div className="max-w-4xl mx-auto py-6 px-4">
                    <h1 className="text-3xl font-bold text-gray-900">
                        Property Report Generator
                    </h1>
                </div>
            </header>
            <main>
                <PropertyReportGenerator/>
            </main>
        </div>
    )
}

export default App