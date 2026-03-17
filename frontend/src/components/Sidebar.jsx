import React from 'react';
import { Home, Upload, Clock, Info, Shield, X, ChevronRight } from 'lucide-react';

const navItems = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'upload', label: 'Upload', icon: Upload },
  { id: 'history', label: 'History', icon: Clock },
  { id: 'about', label: 'About', icon: Info },
];

export default function Sidebar({ activeSection, onNavigate, isOpen, onClose }) {
  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-md z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-full w-[272px] z-40 flex flex-col transition-transform duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]
          ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
        style={{
          background: 'rgba(8, 8, 24, 0.7)',
          backdropFilter: 'blur(32px) saturate(1.5)',
          WebkitBackdropFilter: 'blur(32px) saturate(1.5)',
          borderRight: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        {/* Logo */}
        <div className="px-6 py-7 flex items-center gap-3.5">
          <div
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-blue to-indigo-500 flex items-center justify-center flex-shrink-0"
            style={{ boxShadow: '0 0 20px rgba(0, 212, 255, 0.25)' }}
          >
            <Shield className="w-[18px] h-[18px] text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-bold gradient-text leading-tight">DeepShield</h1>
            <p className="text-[10px] text-white/30 tracking-[0.2em] uppercase leading-tight mt-0.5">AI Detection</p>
          </div>
          <button
            onClick={onClose}
            className="ml-auto lg:hidden p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Divider */}
        <div className="mx-5 h-px bg-gradient-to-r from-transparent via-white/6 to-transparent" />

        {/* Navigation */}
        <nav className="flex-1 px-4 py-5 space-y-1.5">
          <p className="px-3 pb-2 text-[10px] text-white/20 uppercase tracking-[0.15em] font-medium">Navigation</p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all duration-250 group cursor-pointer
                  ${isActive
                    ? 'text-neon-blue'
                    : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
                  }`}
                style={isActive ? {
                  background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.08), rgba(99, 102, 241, 0.06))',
                  border: '1px solid rgba(0, 212, 255, 0.12)',
                  boxShadow: '0 0 16px rgba(0, 212, 255, 0.08), inset 0 1px 0 rgba(255,255,255,0.04)',
                } : { border: '1px solid transparent' }}
              >
                <Icon className={`w-[18px] h-[18px] flex-shrink-0 transition-all duration-200 group-hover:scale-105 ${isActive ? 'text-neon-blue' : ''}`} />
                <span className="text-[13px] font-medium">{item.label}</span>
                {isActive && (
                  <ChevronRight className="w-3.5 h-3.5 ml-auto text-neon-blue/50" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-5">
          <div className="mx-1 h-px bg-gradient-to-r from-transparent via-white/6 to-transparent mb-4" />
          <div
            className="rounded-xl p-3.5 text-center"
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.04)',
            }}
          >
            <p className="text-[10px] text-white/20 tracking-wide">Powered by</p>
            <p className="text-xs font-semibold gradient-text mt-0.5">DeepShield AI v1.0</p>
          </div>
        </div>
      </aside>
    </>
  );
}
