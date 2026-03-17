import React, { useState, useEffect } from 'react';
import { Terminal, Shield } from 'lucide-react';

export default function ExplanationHUD({ notes = [] }) {
  const [displayedNotes, setDisplayedNotes] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < notes.length) {
      const timer = setTimeout(() => {
        setDisplayedNotes((prev) => [...prev, notes[currentIndex]]);
        setCurrentIndex((prev) => prev + 1);
      }, 800); // 800ms delay per line for typewriter-like reporting
      return () => clearTimeout(timer);
    }
  }, [currentIndex, notes]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-white/30 text-[10px] font-bold uppercase tracking-[0.2em]">
          <Terminal className="w-3 h-3" /> Forensic Auditor Log
        </span>
        <div className="flex items-center gap-2 px-2 py-0.5 rounded-full bg-neon-blue/5 border border-neon-blue/20">
          <div className="w-1 h-1 rounded-full bg-neon-blue animate-pulse"></div>
          <span className="text-[9px] text-neon-blue font-bold uppercase tracking-tighter">Live Audit</span>
        </div>
      </div>

      <div className="bg-black/40 border border-white/[0.05] rounded-xl p-5 font-mono text-[11px] leading-relaxed shadow-inner">
        <div className="flex flex-col gap-2.5">
          {displayedNotes.map((note, i) => (
            <div key={i} className="flex gap-3 animate-fade-in">
              <span className="text-neon-blue/40 flex-shrink-0">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
              <span className="text-white/80">
                <span className="text-green-400/80 mr-2">✓</span>
                {note}
              </span>
            </div>
          ))}
          {currentIndex < notes.length && (
            <div className="flex gap-3 animate-pulse">
              <span className="text-neon-blue/40 flex-shrink-0">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
              <span className="text-white/20">Sequencing next signal...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
