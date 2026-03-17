import React, { useState } from 'react';
import { Loader2, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const API_BASE = 'http://localhost:5000';

export default function AnalyzeButton({ inputData, onResult, file, url, activeTab }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleAnalyze = async () => {
    if (!inputData) {
      toast.error('Please provide content to analyze first.');
      return;
    }

    if (activeTab === 'image') {
        // Now supported!
    }

    if (activeTab === 'url') {
        toast.error('URL analysis is currently in beta. Please upload a Video or Image instead.');
        return;
    }

    setLoading(true);
    setProgress(0);
    toast.loading('Initiating forensic analysis...', { id: 'analyze' });

    try {
        // 1. Upload
        const formData = new FormData();
        formData.append('video', file);

        const uploadRes = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!uploadRes.ok) {
            const err = await uploadRes.json();
            throw new Error(err.error || 'Upload failed');
        }

        const { job_id } = await uploadRes.json();
        toast.loading('Processing video frames...', { id: 'analyze' });

        // 2. Poll
        let completed = false;
        let resultData = null;

        while (!completed) {
            await new Promise(r => setTimeout(r, 1500));
            const statusRes = await fetch(`${API_BASE}/status/${job_id}`);
            if (!statusRes.ok) throw new Error('Failed to fetch status');
            
            const data = await statusRes.json();

            if (data.status === 'completed') {
                completed = true;
                resultData = data.result;
            } else if (data.status === 'error') {
                throw new Error(data.error || 'Processing error');
            } else {
                const currentProgress = data.progress || 0;
                setProgress(currentProgress);
                toast.loading(`Forensic Analysis In Progress: ${currentProgress}%`, { id: 'analyze' });
            }
        }

        // 3. Map Result
        // Confidence is "how much it is X". 
        // If it's fake, confidence is risk_score. If it's real, confidence is 100 - risk_score.
        const confidence = resultData.is_deepfake 
            ? resultData.risk_score 
            : (100 - resultData.risk_score);

        const mappedResult = {
            id: job_id,
            verdict: resultData.is_deepfake ? 'Fake' : 'Real',
            confidence: Math.round(confidence),
            explanation: resultData.anomalies.length > 0 
                ? `Anomalies detected: ${resultData.anomalies.join('. ')}` 
                : (resultData.is_deepfake 
                    ? "Deepfake hallmarks detected in biological patterns and frame-level consistency." 
                    : "No significant facial manipulation artifacts detected. Facial biometrics are within normal range."),
            inputType: 'video',
            inputName: file.name,
            timestamp: new Date().toISOString(),
            // Extra metadata for enhanced UI
            riskScore: resultData.risk_score,
            anomalies: resultData.anomalies,
            avgFakeProb: resultData.avg_fake_prob,
            forensicReport: resultData.forensic_report
        };

        // Save to history
        const history = JSON.parse(localStorage.getItem('deepshield-history') || '[]');
        history.unshift(mappedResult);
        if (history.length > 50) history.pop();
        localStorage.setItem('deepshield-history', JSON.stringify(history));

        setLoading(false);
        toast.success(`Analysis complete: ${mappedResult.verdict}`, { id: 'analyze' });
        onResult(mappedResult);

    } catch (err) {
        setLoading(false);
        toast.error(`Error: ${err.message}`, { id: 'analyze' });
    }
  };

  const isDisabled = loading || !inputData;

  return (
    <div className="flex flex-col gap-3 w-full">
        <button
          id="analyze-btn"
          onClick={handleAnalyze}
          disabled={isDisabled}
          className={`w-full px-8 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-3 transition-all duration-300 tracking-wide
            ${loading
              ? 'bg-white/[0.06] text-white/40 cursor-wait'
              : !inputData
                ? 'bg-white/[0.03] text-white/15 cursor-not-allowed border border-white/[0.04]'
                : 'btn-gradient text-white animate-pulse-glow cursor-pointer hover:scale-[1.02] active:scale-[0.98]'
            }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              {progress > 0 ? `Analyzing ${progress}%...` : `Analyzing ${activeTab === 'image' ? 'Image' : 'Video'}...`}
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Analyze {activeTab === 'image' ? 'Image' : 'Video'} Content
            </>
          )}
        </button>
        {loading && progress > 0 && (
            <div className="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                <div 
                    className="h-full bg-neon-blue shadow-[0_0_10px_#00d4ff] transition-all duration-500" 
                    style={{ width: `${progress}%` }}
                />
            </div>
        )}
    </div>
  );
}
