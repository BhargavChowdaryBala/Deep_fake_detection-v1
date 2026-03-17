import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Sidebar.jsx';
import HeroSection from './components/HeroSection.jsx';
import UploadSection from './components/UploadSection.jsx';
import ResultsCard from './components/ResultsCard.jsx';
import HistorySection from './components/HistorySection.jsx';
import AboutSection from './components/AboutSection.jsx';

export default function App() {
  const [activeSection, setActiveSection] = useState('home');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const scrollTo = (id) => {
    setActiveSection(id);
    setSidebarOpen(false);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen">
      {/* Background Orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* Toasts */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: 'rgba(12,12,30,0.92)',
            backdropFilter: 'blur(24px)',
            color: '#e2e8f0',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '14px',
            fontSize: '13px',
            fontWeight: '500',
            padding: '12px 16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          },
          success: { iconTheme: { primary: '#00d4ff', secondary: '#0a0a1a' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0a0a1a' } },
        }}
      />

      {/* Mobile Menu */}
      <button
        id="mobile-menu-btn"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-5 left-5 z-50 p-2.5 rounded-xl lg:hidden transition-all duration-200 hover:scale-105 active:scale-95 cursor-pointer"
        style={{
          background: 'rgba(255,255,255,0.04)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <svg className="w-5 h-5 text-neon-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {sidebarOpen
            ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
            : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
          }
        </svg>
      </button>

      {/* ── LAYOUT ── */}
      <Sidebar
        activeSection={activeSection}
        onNavigate={scrollTo}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main — offset by sidebar on desktop */}
      <main
        className="relative z-10 min-h-screen"
        style={{ marginLeft: '272px' }}
      >

        {/* Hero — full remaining viewport, perfectly centered */}
        <section id="home" className="min-h-screen flex items-center justify-center px-6">
          <HeroSection onStartAnalysis={() => scrollTo('upload')} />
        </section>

        {/* All card sections share ONE centering wrapper */}
        <div className="max-w-3xl mx-auto px-6">

          <div className="section-divider" />

          <section id="upload" className="py-16">
            <UploadSection onResult={setAnalysisResult} />
          </section>

          {analysisResult && (
            <>
              <div className="section-divider" />
              <section id="results" className="py-16 animate-fade-in-up">
                <ResultsCard result={analysisResult} />
              </section>
            </>
          )}

          <div className="section-divider" />

          <section id="history" className="py-16">
            <HistorySection />
          </section>

          <div className="section-divider" />

          <section id="about" className="py-16 pb-28">
            <AboutSection />
          </section>

        </div>
      </main>
    </div>
  );
}
