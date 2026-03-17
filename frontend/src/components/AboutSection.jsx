import React from 'react';
import { Shield, Cpu, Eye, Newspaper, Github, Twitter } from 'lucide-react';

const features = [
  {
    icon: Eye,
    title: 'Image Analysis',
    desc: 'Detects manipulated photos, face-swaps, and AI-generated images using pixel-level analysis.',
  },
  {
    icon: Cpu,
    title: 'Video Detection',
    desc: 'Analyzes frame consistency, audio sync, and temporal patterns to identify deepfake videos.',
  },
  {
    icon: Newspaper,
    title: 'News Verification',
    desc: 'Evaluates text authenticity, source credibility, and AI writing patterns in news articles.',
  },
];

export default function AboutSection() {
  return (
    <div className="w-full flex flex-col gap-10 animate-fade-in-up">
      {/* Header */}
      <div className="text-center flex flex-col items-center gap-3">
        <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
          About <span className="gradient-text">DeepShield AI</span>
        </h2>
        <p className="text-sm text-white/30 max-w-xl leading-relaxed font-light">
          An advanced deepfake detection platform leveraging cutting-edge AI
          to identify manipulated content across images, videos, and text.
        </p>
      </div>

      {/* Features Grid — equal height cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {features.map((feat) => (
          <div
            key={feat.title}
            className="glass glass-hover rounded-2xl p-6 flex flex-col items-center text-center gap-4 group"
          >
            <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
              <feat.icon className="w-5 h-5 text-neon-blue/60" />
            </div>
            <h3 className="text-[15px] font-semibold text-white/85">{feat.title}</h3>
            <p className="text-[13px] text-white/30 leading-relaxed font-light">{feat.desc}</p>
          </div>
        ))}
      </div>

      {/* Tech Stack */}
      <div className="w-full glass-elevated rounded-2xl p-6 flex flex-col gap-4">
        <h3 className="text-[15px] font-semibold text-white/75 flex items-center gap-2">
          <Shield className="w-5 h-5 text-neon-purple/60" />
          Technology Stack
        </h3>
        <div className="flex flex-wrap gap-2.5">
          {['React', 'Tailwind CSS', 'Vite', 'Lucide Icons', 'AI/ML Models', 'WebGL'].map((tech) => (
            <span
              key={tech}
              className="px-4 py-2 rounded-lg text-xs font-medium text-white/35 hover:text-neon-blue/70 transition-colors duration-200 cursor-default bg-white/[0.02] border border-white/[0.04]"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center flex flex-col items-center gap-4 pt-4">
        <div className="h-px w-full bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
        <div className="flex gap-3 pt-2">
          <a href="#" className="p-3 rounded-xl text-white/20 hover:text-neon-blue/60 hover:bg-white/[0.025] transition-all duration-200 border border-white/[0.04]">
            <Github className="w-5 h-5" />
          </a>
          <a href="#" className="p-3 rounded-xl text-white/20 hover:text-neon-blue/60 hover:bg-white/[0.025] transition-all duration-200 border border-white/[0.04]">
            <Twitter className="w-5 h-5" />
          </a>
        </div>
        <p className="text-[11px] text-white/15 tracking-wide font-light">
          © 2026 DeepShield AI · Built for Hackathon
        </p>
      </div>
    </div>
  );
}
