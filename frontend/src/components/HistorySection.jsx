import React, { useState, useEffect } from 'react';
import { Clock, Trash2, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

export default function HistorySection() {
  const [history, setHistory] = useState([]);
  const [expanded, setExpanded] = useState(null);

  const loadHistory = () => {
    const data = JSON.parse(localStorage.getItem('deepshield-history') || '[]');
    setHistory(data);
  };

  useEffect(() => {
    loadHistory();
    const interval = setInterval(loadHistory, 2000);
    return () => clearInterval(interval);
  }, []);

  const clearHistory = () => {
    localStorage.removeItem('deepshield-history');
    setHistory([]);
    toast.success('History cleared');
  };

  return (
    <div className="w-full flex flex-col gap-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Analysis <span className="gradient-text">History</span>
          </h2>
          <p className="text-sm text-white/25 font-light">{history.length} analyses recorded</p>
        </div>
        {history.length > 0 && (
          <button
            id="clear-history-btn"
            onClick={clearHistory}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-red-400/60 hover:text-red-400 hover:bg-red-500/[0.06] transition-all duration-200 text-[13px] font-medium cursor-pointer border border-red-400/10"
          >
            <Trash2 className="w-4 h-4" />
            Clear All
          </button>
        )}
      </div>

      {/* History List */}
      {history.length === 0 ? (
        <div className="w-full glass-elevated rounded-2xl p-14 text-center flex flex-col items-center gap-3">
          <div className="w-14 h-14 rounded-xl bg-white/[0.03] flex items-center justify-center">
            <Clock className="w-7 h-7 text-white/10" />
          </div>
          <p className="text-white/25 text-[15px] font-medium">No analyses yet</p>
          <p className="text-white/15 text-sm font-light">Your analysis history will appear here</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {history.map((item) => {
            const isFake = item.verdict === 'Fake';
            const isExpanded = expanded === item.id;
            return (
              <div
                key={item.id}
                className="w-full glass glass-hover rounded-xl overflow-hidden cursor-pointer"
                onClick={() => setExpanded(isExpanded ? null : item.id)}
              >
                <div className="px-5 py-4 flex items-center gap-4">
                  {/* Icon — centered */}
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      isFake ? 'bg-red-500/8 text-red-400/70' : 'bg-green-500/8 text-green-400/70'
                    }`}
                  >
                    {isFake ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-[13px] font-semibold ${isFake ? 'text-red-400/80' : 'text-green-400/80'}`}>
                        {item.verdict}
                      </span>
                      <span className="text-white/10">·</span>
                      <span className="text-xs text-white/20 capitalize font-light">{item.inputType}</span>
                    </div>
                    <p className="text-xs text-white/15 truncate font-light">{item.inputName}</p>
                  </div>

                  {/* Confidence */}
                  <div className="text-right flex-shrink-0 flex flex-col items-end gap-0.5">
                    <span className={`text-sm font-bold tabular-nums ${isFake ? 'text-red-400/70' : 'text-green-400/70'}`}>
                      {item.confidence}%
                    </span>
                    <span className="text-[10px] text-white/15">{new Date(item.timestamp).toLocaleDateString()}</span>
                  </div>

                  {/* Expand */}
                  <div className="text-white/15 flex-shrink-0">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-4 pt-3 border-t border-white/[0.03] animate-fade-in">
                    <p className="text-[13px] text-white/35 leading-relaxed font-light">{item.explanation}</p>
                    <p className="text-[11px] text-white/15 mt-2">{new Date(item.timestamp).toLocaleString()}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
