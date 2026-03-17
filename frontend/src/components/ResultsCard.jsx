import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert, TrendingUp, FileType, Clock, Lightbulb, Activity } from 'lucide-react';

export default function ResultsCard({ result }) {
  const [animatedConfidence, setAnimatedConfidence] = useState(0);
  const isFake = result.verdict === 'Fake';

  useEffect(() => {
    setAnimatedConfidence(0);
    const timer = setTimeout(() => setAnimatedConfidence(result.confidence), 100);
    return () => clearTimeout(timer);
  }, [result]);

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Header */}
      <div className="text-center flex flex-col items-center gap-2">
        <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
          Analysis <span className="gradient-text">Results</span>
        </h2>
      </div>

      {/* Main Card */}
      <div className="w-full glass-elevated rounded-2xl p-6 sm:p-8 flex flex-col gap-7">
        
        {/* New Multi-Probability Display */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-8 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <div className="text-center flex-1">
                <p className="text-[10px] text-white/30 uppercase tracking-[0.2em] font-bold mb-2">Real (Authentic)</p>
                <p className="text-5xl font-black text-green-400 drop-shadow-[0_0_15px_rgba(74,222,128,0.3)] tabular-nums">
                    {(100 - (result.riskScore || result.confidence)).toFixed(1)}%
                </p>
            </div>

            <div className="h-12 w-px bg-white/10 hidden md:block"></div>
            <div className="w-full h-px bg-white/10 md:hidden"></div>

            <div className="text-center flex-1">
                <p className="text-[10px] text-white/30 uppercase tracking-[0.2em] font-bold mb-2">AI-Generated (Fake)</p>
                <p className="text-5xl font-black text-red-400 drop-shadow-[0_0_15px_rgba(248,113,113,0.3)] tabular-nums">
                    {(result.riskScore || result.confidence).toFixed(1)}%
                </p>
            </div>
        </div>

        {/* Verdict Banner */}
        <div className={`flex items-center justify-center gap-3 py-3 px-6 rounded-xl border ${
            isFake ? 'bg-red-500/5 border-red-500/20 text-red-400' : 'bg-green-500/5 border-green-500/20 text-green-400'
        }`}>
            {isFake ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            <span className="text-lg font-bold uppercase tracking-widest">
                System Verdict: {isFake ? 'MANIPULATION DETECTED' : 'CONTENT IS AUTHENTIC'}
            </span>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-5 flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-white/25 text-[10px] uppercase tracking-[0.15em] font-medium">
              <FileType className="w-3.5 h-3.5" /> Media Type
            </span>
            <span className="text-white/70 font-semibold text-sm capitalize">{result.inputType}</span>
          </div>
          <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-5 flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-white/25 text-[10px] uppercase tracking-[0.15em] font-medium">
              <TrendingUp className="w-3.5 h-3.5" /> Frame Bias
            </span>
            <span className="text-white/70 font-semibold text-sm">{result.avgFakeProb || result.confidence}%</span>
          </div>
          <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-5 flex flex-col gap-1.5 overflow-hidden">
            <span className="flex items-center gap-1.5 text-white/25 text-[10px] uppercase tracking-[0.15em] font-medium">
              <Clock className="w-3.5 h-3.5" /> Analysis Time
            </span>
            <span className="text-white/70 font-semibold text-[11px] truncate">
              {new Date(result.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Forensic Intelligence */}
        {result.forensicReport && (
            <div className="flex flex-col gap-4">
                <span className="flex items-center gap-2 text-white/30 text-[10px] font-bold uppercase tracking-[0.2em] mb-1">
                    <Activity className="w-3 h-3" /> Forensic Intelligence Report
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(result.forensicReport).map(([key, data]) => (
                        <div key={key} className="bg-white/[0.01] border border-white/[0.04] p-4 rounded-xl flex flex-col gap-3 transition-all hover:bg-white/[0.02] hover:border-white/[0.08]">
                            <div className="flex items-center justify-between">
                                <span className="text-white/60 text-xs font-semibold">{data.label}</span>
                                <span className={`text-[9px] font-black px-2 py-0.5 rounded border ${
                                    data.status === 'danger' 
                                        ? 'text-red-400 bg-red-400/10 border-red-400/20' 
                                        : data.status === 'warning' 
                                            ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20'
                                            : 'text-green-400 bg-green-400/10 border-green-400/20'
                                }`}>
                                    {data.status.toUpperCase()}
                                </span>
                            </div>
                            
                            <div className="flex flex-col gap-1.5">
                                <div className="flex justify-between items-end">
                                    <span className="text-[10px] text-white/20 font-medium">Analysis Signal</span>
                                    <span className="text-[10px] text-white/40 font-mono">{Math.round(data.score)}%</span>
                                </div>
                                <div className="h-1 w-full bg-white/[0.03] rounded-full overflow-hidden">
                                    <div 
                                        className={`h-full rounded-full transition-all duration-1000 ease-out shadow-[0_0_8px_rgba(255,255,255,0.1)] ${
                                            data.status === 'danger' ? 'bg-red-400' : data.status === 'warning' ? 'bg-yellow-400' : 'bg-green-400'
                                        }`}
                                        style={{ width: `${Math.max(5, data.score)}%` }}
                                    />
                                </div>
                            </div>
                            
                            <p className="text-[10px] text-white/25 leading-relaxed font-light italic">
                                "{data.description}"
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* Forensic Anomalies */}
        {result.anomalies && result.anomalies.length > 0 && (
            <div className="flex flex-col gap-3">
                <span className="flex items-center gap-2 text-red-400/70 text-[11px] font-bold uppercase tracking-widest">
                    <ShieldAlert className="w-3.5 h-3.5" /> Detected Anomalies
                </span>
                <div className="grid grid-cols-1 gap-2">
                    {result.anomalies.map((an, i) => (
                        <div key={i} className="text-xs text-white/50 bg-white/[0.02] p-3 rounded-lg border border-white/[0.05] flex items-center gap-2">
                            <div className="w-1 h-1 rounded-full bg-red-400"></div>
                            {an}
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* Explanation */}
        <div className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-5 flex flex-col gap-2">
          <span className="flex items-center gap-2 text-neon-blue/70 text-[13px] font-semibold">
            <Lightbulb className="w-4 h-4" /> AI Analyst Conclusion
          </span>
          <p className="text-white/45 text-sm leading-relaxed font-light">{result.explanation}</p>
        </div>
      </div>
    </div>
  );
}
