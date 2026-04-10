import React, { useState } from 'react';
import RPSCalculator from './components/RPSCalculator';
import ObserverDemo from './components/ObserverDemo';
// import './styles/custom.scss';
import './styles/index.css';

function App() {
  const [page, setPage] = useState('observer'); // observer | calculator

  const NavButton = ({ id, label }) => (
    <button
      onClick={() => setPage(id)}
      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
        page === id
          ? 'bg-blue-600 text-white shadow'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
      aria-current={page === id ? 'page' : undefined}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Simple nav: switch between Observer and RPS Calculator */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="text-lg font-semibold mr-10 ">Page Change:  </div>
          <NavButton id="observer" label="Observer" />
          <NavButton id="calculator" label="RPS Calculator" />
        </div>
      </nav>

      <main className="py-8">
        {page === 'observer' ? <ObserverDemo /> : <RPSCalculator />}
      </main>
    </div>
  );
}

export default App;
