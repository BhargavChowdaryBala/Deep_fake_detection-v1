import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { ShieldCheckIcon, ShieldExclamationIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';

export default function SecurityHUD() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, completed, error
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const onDrop = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setStatus('idle');
      setResult(null);
      setProgress(0);
      setErrorMsg('');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi']
    },
    maxFiles: 1
  });

  const uploadVideo = async () => {
    if (!file) return;
    setStatus('uploading');
    
    const formData = new FormData();
    formData.append('video', file);

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      
      if (response.ok) {
        setJobId(data.job_id);
        setStatus('processing');
      } else {
        setStatus('error');
        setErrorMsg(data.error || 'Upload failed');
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg('Failed to connect to server');
    }
  };

  // Poll for status
  useEffect(() => {
    let intervalId;
    
    if (status === 'processing' && jobId) {
      intervalId = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:5000/status/${jobId}`);
          const data = await response.json();
          
          if (data.status === 'completed') {
            setStatus('completed');
            setProgress(100);
            setResult(data.result);
            clearInterval(intervalId);
          } else if (data.status === 'error') {
            setStatus('error');
            setErrorMsg(data.error);
            clearInterval(intervalId);
          } else {
             // In progress
             setProgress(data.progress || 0);
          }
        } catch (err) {
           console.error("Polling error:", err);
        }
      }, 1000);
    }
    
    return () => clearInterval(intervalId);
  }, [status, jobId]);

  const downloadJSON = () => {
      if(!result) return;
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(result, null, 2));
      const downloadAnchorNode = document.createElement('a');
      downloadAnchorNode.setAttribute("href",     dataStr);
      downloadAnchorNode.setAttribute("download", `forensic_report_${file?.name || 'video'}.json`);
      document.body.appendChild(downloadAnchorNode); 
      downloadAnchorNode.click();
      downloadAnchorNode.remove();
  };

  return (
    <div className="w-full max-w-5xl p-6 bg-squid-charcoal border-2 border-gray-700 rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.5)] font-mono flex flex-col gap-6 text-gray-200">
      
      {/* Header */}
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h1 className="text-2xl font-bold tracking-widest uppercase text-white">
          Forensic Lab
          <span className="ml-2 py-1 px-2 text-xs bg-gray-800 rounded opacity-70">BATCH MODE</span>
        </h1>
        <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${status === 'processing' ? 'bg-squid-mint animate-pulse' : 'bg-gray-600'}`}></span>
            <span className="text-sm tracking-wider">{status === 'processing' ? 'PROCESSING' : 'STANDBY'}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Upload & Progress */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          
          <div 
             {...getRootProps()} 
             className={`border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors
               ${isDragActive ? 'border-squid-mint bg-squid-mint/10' : 'border-gray-600 hover:border-gray-400 bg-black/30'}
             `}
          >
            <input {...getInputProps()} className="hidden" />
            <DocumentArrowDownIcon className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-sm font-semibold mb-2">Drag & Drop Target Video</p>
            <p className="text-xs text-gray-500">MP4, MOV up to 500MB</p>
            {file && <div className="mt-4 p-2 bg-gray-800 rounded w-full border border-gray-700 truncate text-sm text-squid-mint">{file.name}</div>}
          </div>

          <button 
             onClick={uploadVideo}
             disabled={!file || status === 'uploading' || status === 'processing'}
             className={`p-3 rounded font-bold tracking-wider transition-all uppercase 
               ${!file || status === 'uploading' || status === 'processing' 
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed' 
                  : 'bg-squid-mint text-black hover:bg-[#02A03E] shadow-[0_0_15px_#03C04A]'
               }
             `}
          >
             {status === 'uploading' ? 'Uploading...' : 'Commence Analysis'}
          </button>

          {/* Progress Bar */}
          {(status === 'uploading' || status === 'processing') && (
            <div className="bg-black/50 p-4 rounded-lg border border-gray-800">
                <div className="flex justify-between text-xs mb-2 uppercase text-gray-400">
                    <span>Extraction & Neural Pass</span>
                    <span>{progress}%</span>
                </div>
                <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden relative">
                    <div 
                        className="absolute top-0 left-0 h-full bg-squid-mint transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
            </div>
          )}
          
          {status === 'error' && (
              <div className="p-3 bg-red-900/40 border border-red-500 text-red-400 text-xs rounded">
                  ERROR: {errorMsg}
              </div>
          )}
        </div>

        {/* Right Col: Verdict Card */}
        <div className="lg:col-span-2 flex flex-col gap-6">
           <div className={`flex-1 border-2 rounded-lg p-6 flex flex-col justify-center items-center transition-all bg-black/40 relative overflow-hidden
               ${status === 'completed' 
                  ? (result?.is_deepfake ? 'border-squid-pink shadow-[0_0_20px_#FF007F]' : 'border-squid-mint shadow-[0_0_20px_#03C04A]')
                  : 'border-gray-800'}
           `}>
                
                {status !== 'completed' ? (
                    <div className="text-center opacity-30 flex flex-col items-center">
                        <ShieldCheckIcon className="w-24 h-24 mb-4" />
                        <p className="tracking-widest uppercase">Awaiting Target Data</p>
                    </div>
                ) : (
                     <div className="w-full animate-[fadeIn_0.5s_ease-out]">
                       <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-8 bg-gray-900/50 p-6 rounded-lg border border-gray-800">
                           <div className="text-center flex-1">
                               <h2 className="text-xs tracking-[0.2em] text-gray-500 mb-2 uppercase font-bold">Real (Authentic)</h2>
                               <span className="text-6xl font-black text-squid-mint drop-shadow-[0_0_15px_#03C04A]">
                                  {(100 - result.risk_score).toFixed(1)}%
                               </span>
                           </div>
                           
                           <div className="h-16 w-px bg-gray-800 hidden md:block"></div>
                           <div className="w-full h-px bg-gray-800 md:hidden"></div>

                           <div className="text-center flex-1">
                               <h2 className="text-xs tracking-[0.2em] text-gray-500 mb-2 uppercase font-bold">AI-Generated (Fake)</h2>
                               <span className="text-6xl font-black text-squid-pink drop-shadow-[0_0_15px_#FF007F]">
                                  {result.risk_score.toFixed(1)}%
                               </span>
                           </div>
                       </div>

                       <div className="grid grid-cols-2 gap-4 mb-8">
                           <div className="bg-gray-900 border border-gray-800 p-4 rounded">
                               <p className="text-xs text-gray-500 uppercase mb-1">Avg Frame ConvNeXt Prob</p>
                               <span className="text-lg text-white">{result.avg_fake_prob}%</span>
                           </div>
                           <div className="bg-gray-900 border border-gray-800 p-4 rounded">
                               <p className="text-xs text-gray-500 uppercase mb-1">Frames Analyzed</p>
                               <span className="text-lg text-white">{result.frames_analyzed}</span>
                           </div>
                       </div>

                       {/* Timeline / Anomalies */}
                       <div className="mb-8">
                           <h3 className="text-xs tracking-[0.2em] text-gray-400 uppercase mb-3 border-b border-gray-800 pb-2">Forensic Timeline & Anomalies</h3>
                           <div className="max-h-32 overflow-y-auto pr-2 space-y-2 text-sm">
                               {result.anomalies.map((an, i) => (
                                   <div key={`an-${i}`} className="text-squid-pink bg-squid-pink/10 p-2 rounded border border-squid-pink/30 flex items-center gap-2">
                                       <div className="w-1.5 h-1.5 rounded-full bg-squid-pink"></div>
                                       {an}
                                   </div>
                               ))}
                               {result.anomalies.length === 0 && <div className="text-gray-500 italic">No global behavioral anomalies detected.</div>}
                           </div>
                       </div>

                       {/* Action */}
                       <div className="flex justify-end border-t border-gray-800 pt-6">
                            <button 
                                onClick={downloadJSON}
                                className="flex items-center gap-2 px-4 py-2 border border-gray-600 hover:border-white text-sm tracking-wider uppercase transition-colors"
                            >
                                <DocumentArrowDownIcon className="w-5 h-5" />
                                Export JSON Report
                            </button>
                       </div>
                    </div>
                )}
           </div>
        </div>
      </div>
    </div>
  );
}
