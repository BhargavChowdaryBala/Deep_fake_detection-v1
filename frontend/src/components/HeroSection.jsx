import React, { useEffect, useState } from 'react';
import { Shield, Scan, Zap, ArrowRight, Sparkles } from 'lucide-react';

export default function HeroSection({ onStartAnalysis }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      className={`w-full max-w-4xl mx-auto text-center flex flex-col items-center justify-center gap-8 px-4 transition-all duration-1000 ease-out
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
    >
      {/* Radial glow behind hero */}
      <div className="hero-glow" />

      {/* Badge */}
      <div className="inline-flex items-center gap-2.5 px-5 py-2.5 glass-elevated rounded-full text-sm font-medium text-neon-blue/90 animate-badge-glow">
        <Sparkles className="w-3.5 h-3.5" />
        <span className="tracking-wide">AI-Powered Detection Engine</span>
      </div>

      {/* Title Block */}
      <div className="flex flex-col items-center gap-3">
        <h1 className="text-6xl sm:text-7xl md:text-8xl lg:text-[6.5rem] font-black tracking-tighter leading-[0.9]">
          <span className="gradient-text glow-text-blue">DeepShield</span>
        </h1>
        <h2 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-white/85 tracking-tight leading-none">
          AI
        </h2>
      </div>

      {/* Subtitle */}
      <p className="text-base sm:text-lg md:text-xl text-white/45 max-w-xl leading-relaxed font-light">
        Detect{' '}
        <span className="text-neon-blue font-medium">Fake Videos</span>,{' '}
        <span className="text-neon-purple font-medium">Images</span> &{' '}
        <span className="text-neon-pink font-medium">News</span>{' '}
        Instantly
        <br />
        <span className="text-white/30 text-sm sm:text-base">
          using advanced AI-powered analysis
        </span>
      </p>

      {/* Feature Pills */}
      <div className="flex flex-wrap justify-center gap-3">
        {[
          { icon: Scan, label: 'Image Detection' },
          { icon: Shield, label: 'Video Analysis' },
          { icon: Zap, label: 'News Verification' },
        ].map((feat, i) => (
          <div
            key={feat.label}
            className="glass glass-hover px-4 py-2.5 rounded-full flex items-center gap-2 text-[13px] text-white/50 font-medium cursor-default"
            style={{ animationDelay: `${i * 120}ms` }}
          >
            <feat.icon className="w-3.5 h-3.5 text-neon-blue/60" />
            {feat.label}
          </div>
        ))}
      </div>

      {/* CTA Button */}
      <button
        id="cta-start-analysis"
        onClick={onStartAnalysis}
        className="group btn-gradient mt-2 px-12 py-5 rounded-2xl text-white font-bold text-lg inline-flex items-center gap-3 animate-pulse-glow cursor-pointer tracking-wide hover:scale-[1.03] active:scale-[0.98] transition-transform duration-200"
      >
        Start Analysis
        <ArrowRight className="w-5 h-5 transition-all duration-300 group-hover:translate-x-1.5 group-hover:scale-110" />
      </button>

      {/* Trust Bar */}
      <div className="flex items-center justify-center gap-6 sm:gap-8 pt-2">
        {[
          { value: '99.2%', label: 'Accuracy' },
          { value: 'Real-time', label: 'Results' },
          { value: '50K+', label: 'Scans' },
        ].map((stat) => (
          <div key={stat.label} className="flex flex-col items-center gap-0.5">
            <span className="text-xs sm:text-sm font-semibold text-white/25">{stat.value}</span>
            <span className="text-[10px] text-white/15 uppercase tracking-widest">{stat.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
